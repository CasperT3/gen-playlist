import requests
import re
import concurrent.futures
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

def fetch_content(url):
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.text
    except requests.RequestException as e:
        print(f"Error fetching content: {e}")
        return None

def is_valid_url(url):
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except ValueError:
        return False

# Cache for storing URL validation results
url_cache = {}

def check_stream(url, timeout=8, max_attempts=1):
    """Check if a stream URL is accessible and actually playable."""
    # Check cache first
    if url in url_cache:
        return url_cache[url]
        
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': '*/*',
        'Connection': 'close',  # Close connection after request
        'Referer': 'https://www.google.com/'
    }
    
    for attempt in range(max_attempts):
        try:
            # For m3u8 and m3u playlists
            if url.endswith(('.m3u8', '.m3u')):
                # First check if the playlist is accessible
                response = requests.head(url, headers=headers, timeout=timeout, allow_redirects=True, stream=False, verify=False)
                if response.status_code != 200:
                    return False, url
                
                # For m3u8, try to fetch and parse the playlist
                if url.endswith('.m3u8'):
                    response = requests.get(url, headers=headers, timeout=timeout, stream=False, verify=False)
                    if response.status_code == 200:
                        content = response.text
                        # Check if it's a valid m3u8 playlist
                        if '#EXTM3U' not in content:
                            result = (False, url)
                            url_cache[url] = result
                            return result
                            
                        # For master playlists, check if we can access at least one variant
                        if '#EXT-X-STREAM-INF' in content:
                            # Try to find a variant URL
                            import re
                            variant_urls = re.findall(r'\n([^\n\.]+\.m3u8[^\n]*)', content)
                            if variant_urls:
                                # Try the first variant
                                variant_url = variant_urls[0]
                                if not variant_url.startswith('http'):
                                    # Handle relative URLs
                                    from urllib.parse import urljoin
                                    variant_url = urljoin(url, variant_url)
                                return check_stream(variant_url, timeout, 1)  # Only try once for variants
                        
                        # For simple playlists, check if there are segments
                        if '#EXTINF' in content and ('.ts' in content or 'EXT-X-MEDIA-SEQUENCE' in content):
                            result = (True, url)
                            url_cache[url] = result
                            return result
                            
                        result = (False, url)
                        url_cache[url] = result
                        return result
            
            # For direct video streams
            else:
                # Try a range request first
                range_headers = headers.copy()
                range_headers['Range'] = 'bytes=0-1024'  # Request first KB
                
                with requests.get(url, headers=range_headers, timeout=timeout, stream=True) as response:
                    if response.status_code in (200, 206):
                        # Read a small chunk to verify content
                        chunk = next(response.iter_content(chunk_size=1024), None)
                        if not chunk:
                            result = (False, url)
                            url_cache[url] = result
                            return result
                            
                        # Check content type to ensure it's a video/audio stream
                        content_type = response.headers.get('Content-Type', '').lower()
                        if not any(x in content_type for x in ['video/', 'audio/', 'application/octet-stream', 'application/vnd.apple.mpegurl']):
                            result = (False, url)
                            url_cache[url] = result
                            return result
                            
                        result = (True, url)
                        url_cache[url] = result
                        return result
                    
        except (requests.RequestException, Exception) as e:
            if attempt == max_attempts - 1:
                return False, url
            time.sleep(1)  # Small delay before retry
            continue
            
    return False, url

def convert_to_m3u(content, output_file, max_workers=20):  # Increased max_workers
    lines = content.split('\n')
    current_group = ""
    
    # EPG and logo configuration
    EPG_URL = "https://epgshare01.online/epgshare01/epg_ripper_DUMMY_CHANNELS.xml.gz"
    TVG_ID = "Blank.Dummy.us"
    LOGO_URL = "https://github.com/BuddyChewChew/gen-playlist/blob/main/docs/chb.png?raw=true"
    
    # M3U header with EPG URL
    m3u_lines = [
        "#EXTM3U x-tvg-url=\"" + EPG_URL + "\"",
        "#EXT-X-TVG-URL: " + EPG_URL
    ]
    
    entries = []
    
    # First, parse all entries
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        if line.endswith(',#genre#'):
            current_group = line.split(',#genre#')[0].strip()
            entries.append(('group', current_group, None))
        elif ',' in line and is_valid_url(line.split(',')[-1]):
            parts = line.rsplit(',', 1)
            if len(parts) == 2 and is_valid_url(parts[1]):
                name, url = parts
                entries.append(('stream', name.strip(), url.strip(), current_group))
    
    # Process streams in parallel
    valid_streams = []
    stream_entries = [e for e in entries if e[0] == 'stream']
    
    print(f"Checking {len(stream_entries)} streams for availability...")
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_entry = {
            executor.submit(check_stream, entry[2]): entry 
            for entry in stream_entries
        }
        
        for future in concurrent.futures.as_completed(future_to_entry):
            entry = future_to_entry[future]
            try:
                is_valid, url = future.result()
                if is_valid:
                    valid_streams.append((entry[1], url, entry[3]))
                    print(f"✓ {entry[1]}")
                else:
                    print(f"✗ {entry[1]} (unreachable)")
            except Exception as e:
                print(f"✗ {entry[1]} (error: {str(e)})")
    
    # Build the final M3U file
    current_group = ""
    seen_urls = set()  # Track seen URLs to avoid duplicates
    
    for entry in entries:
        if entry[0] == 'group':
            current_group = entry[1]
            m3u_lines.append(f"#EXTINF:-1 tvg-id=\"{TVG_ID}\" group-title=\"{current_group}\",{current_group}")
            m3u_lines.append("#" + current_group)  # Add as comment
        else:
            # Only add stream if it's in the valid_streams list and URL not seen before
            stream_match = next(
                (s for s in valid_streams 
                 if s[0] == entry[1] and s[2] == current_group and s[1] == entry[2] 
                 and s[1] not in seen_urls),
                None
            )
            if stream_match:
                seen_urls.add(stream_match[1])  # Mark URL as seen
                m3u_lines.append(f"#EXTINF:-1 tvg-id=\"{TVG_ID}\" tvg-logo=\"{LOGO_URL}\" group-title=\"{current_group}\",{entry[1].split(' ', 1)[0] if ' ' in entry[1] else entry[1]}")
                m3u_lines.append(stream_match[1])
    
    print(f"\nFound {len(valid_streams)}/{len(stream_entries)} working streams")
    
    # Write to file
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(m3u_lines))
    
    print(f"Successfully converted to {output_file}")

def main():
    # Direct URL for the playlist
    url = "https://raw.githubusercontent.com/jack2713/my/refs/heads/main/my02.txt"
    output_file = "playlist.m3u"
        
    print(f"Fetching content from the provided URL...")
    content = fetch_content(url)
    
    if content:
        print("Converting to M3U format and checking stream availability...")
        start_time = time.time()
        convert_to_m3u(content, output_file)
        end_time = time.time()
        print(f"\nProcessing completed in {end_time - start_time:.2f} seconds")
    else:
        print("Failed to fetch content. Please check the URL and try again.")

if __name__ == "__main__":
    main()
