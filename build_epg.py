import os
import re
import urllib.request
import urllib.error
import urllib.parse
from datetime import datetime, timedelta
import ssl
import json

# Ignore SSL errors
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

M3U_PATH = "ip-tv.m3u"
EPG_PATH = "epg.xml"
ASSETS_DIR = "assets/channel"

def sanitize_filename(name):
    return re.sub(r'[^a-zA-Z0-9]', '_', name).strip('_').lower() + '.png'

def search_logo(channel_name):
    print(f"Searching logo for {channel_name}...")
    # Try clearbit first
    try:
        url = f"https://autocomplete.clearbit.com/v1/companies/suggest?query={urllib.parse.quote(channel_name)}"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        response = urllib.request.urlopen(req, context=ctx)
        data = json.loads(response.read().decode('utf-8'))
        if data and len(data) > 0 and 'logo' in data[0]:
            return data[0]['logo']
    except Exception as e:
        pass
    
    # Try a free icon service as fallback (ui-avatars for initials)
    initials = "".join([w[0] for w in channel_name.split() if w])[:2].upper()
    if not initials:
        initials = "TV"
    return f"https://ui-avatars.com/api/?name={initials}&background=random&color=fff&size=256"

def download_image(url, save_path):
    if os.path.exists(save_path):
        return True
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, context=ctx, timeout=5) as response, open(save_path, 'wb') as out_file:
            out_file.write(response.read())
        return True
    except Exception as e:
        print(f"Failed to download {url}: {e}")
        return False

with open(M3U_PATH, 'r') as f:
    lines = f.readlines()

channels = []
current_channel = {}
for line in lines:
    line = line.strip()
    if line.startswith('#EXTINF:'):
        tvg_id = re.search(r'tvg-id="([^"]*)"', line)
        tvg_name = re.search(r'tvg-name="([^"]*)"', line)
        tvg_logo = re.search(r'tvg-logo="([^"]*)"', line)
        
        # fallback name parsing
        fallback_name = ""
        if "," in line:
            fallback_name = line.split(",")[-1].strip()
            
        c_id = tvg_id.group(1) if tvg_id else ""
        c_name = tvg_name.group(1) if tvg_name else fallback_name
        c_logo = tvg_logo.group(1) if tvg_logo else ""
        
        current_channel = {
            'id': c_id,
            'name': c_name,
            'logo': c_logo
        }
    elif line.startswith('http') or line.startswith('rtmp'):
        if current_channel:
            current_channel['url'] = line
            channels.append(current_channel)
            current_channel = {}

# Process icons
unique_epg_channels = {}
for c in channels:
    # If no ID, generate one from name
    if not c['id']:
        c['id'] = sanitize_filename(c['name']).replace('.png', '')
        
    if c['id'] not in unique_epg_channels:
        # Determine logo URL
        logo_url = c['logo']
        if not logo_url:
            logo_url = search_logo(c['name'])
            c['logo'] = logo_url
            
        # Download logo
        local_filename = sanitize_filename(c['name'])
        local_filepath = os.path.join(ASSETS_DIR, local_filename)
        
        if logo_url:
            success = download_image(logo_url, local_filepath)
            if success:
                # Use absolute path for Jellyfin
                abs_path = os.path.abspath(local_filepath)
                c['local_logo'] = f"file://{abs_path}"
            else:
                c['local_logo'] = ""
        else:
            c['local_logo'] = ""
            
        unique_epg_channels[c['id']] = c

# Generate EPG
xml_content = ['<?xml version="1.0" encoding="UTF-8"?>', '<tv>']
for ch_id, c in unique_epg_channels.items():
    name_esc = c["name"].replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    logo_esc = c.get("local_logo", "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    
    xml_content.append(f'  <channel id="{ch_id}">')
    xml_content.append(f'    <display-name>{name_esc}</display-name>')
    if logo_esc:
        xml_content.append(f'    <icon src="{logo_esc}" />')
    xml_content.append('  </channel>')

start_time = datetime.utcnow().strftime("%Y%m%d%H%M%S +0000")
end_time = (datetime.utcnow() + timedelta(days=7)).strftime("%Y%m%d%H%M%S +0000")

for ch_id, c in unique_epg_channels.items():
    name_esc = c["name"].replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    logo_esc = c.get("local_logo", "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    
    xml_content.append(f'  <programme start="{start_time}" stop="{end_time}" channel="{ch_id}">')
    xml_content.append(f'    <title>{name_esc} Broadcast</title>')
    xml_content.append(f'    <desc>Live Stream for {name_esc}</desc>')
    if logo_esc:
        xml_content.append(f'    <icon src="{logo_esc}" />')
    xml_content.append('  </programme>')

xml_content.append('</tv>')

with open(EPG_PATH, 'w') as f:
    f.write('\n'.join(xml_content))

print(f"Successfully processed {len(unique_epg_channels)} unique channels and saved EPG.")
