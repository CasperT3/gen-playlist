{{ ... }}

def server1(i, name):
    print("Running Server 1")
    url = f"https://adult-tv-channels.com/tv/{name}.php"
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Referer": "https://adult-tv-channels.com",
        "X-Requested-With": "XMLHttpRequest",
    }

    response = requests.get(url, headers=headers, verify=certifi.where())

    # Use regex to extract the source URL
    match = re.search(r'file:\s*"([^"]+playlist\.m3u8[^"]*)"', response.text)
    if match:
        stream_url = match.group(1)
        with open("docs/combined_playlist.m3u", "a", encoding='utf-8-sig') as file:
            file.write(f'#EXTINF:-1 tvg-id="Adult.Programming.Dummy.us" tvg-name="{name}" tvg-logo="{CHANNEL_LOGO}" group-title="Adult 1",{name}\n')
            file.write(f"{stream_url}\n")
    else:
        print("No URL found.")


def server2(hash, name):
    print("Running Server 2")
    try:
        res = requests.post(
            f"https://adult-tv-channels.click/C1Ep6maUdBIeKDQypo7a/{hash}",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=10
        )
        data = res.json()
        token = data["fileUrl"]
        stream_url = f"https://moonlight.wideiptv.top/{name}/index.fmp4.m3u8?token={token}"
        with open("docs/combined_playlist.m3u", "a", encoding='utf-8-sig') as file:
            file.write(f'#EXTINF:-1 tvg-id="Adult.Programming.Dummy.us" tvg-name="{name}" tvg-logo="{CHANNEL_LOGO}" group-title="Adult 2",{name}\n')
            file.write(f"{stream_url}\n")
    except Exception as e:
        print(f"Error processing {name}: {str(e)}")


def server3(hash, name):
    print("Running Server 3")
    try:
        url = f"https://fuckflix.click/8RLxsc2AW1q8pvyvjqIQ"
        res = requests.post(
            f"{url}/{hash}", 
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=10
        )
        data = res.json()
        token = data["fileUrl"]
        stream_url = f"https://moonlight.wideiptv.top/{name}/index.fmp4.m3u8?token={token}"
        with open("docs/combined_playlist.m3u", "a", encoding='utf-8-sig') as file:
            file.write(f'#EXTINF:-1 tvg-id="Adult.Programming.Dummy.us" tvg-name="{name}" tvg-logo="{CHANNEL_LOGO}" group-title="Adult 3",{name}\n')
            file.write(f"{stream_url}\n")
    except Exception as e:
        print(f"Error processing {name}: {str(e)}")
{{ ... }}
