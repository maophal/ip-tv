import http.server
import socketserver
import json
import os
import re
from datetime import datetime, timedelta

PORT = 8000
DIRECTORY = "static"
M3U_PATH = "../ip-tv.m3u"
EPG_PATH = "../epg.xml"

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def do_GET(self):
        if self.path == '/api/channels':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            channels = self.read_channels()
            self.wfile.write(json.dumps(channels).encode('utf-8'))
        else:
            return http.server.SimpleHTTPRequestHandler.do_GET(self)

    def do_POST(self):
        if self.path == '/api/channels':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            channels = json.loads(post_data.decode('utf-8'))
            
            self.save_channels(channels)
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "success"}).encode('utf-8'))
        else:
            self.send_error(404)

    def read_channels(self):
        # Parse M3U
        try:
            with open(M3U_PATH, 'r') as f:
                lines = f.readlines()
        except FileNotFoundError:
            return []

        channels = []
        current_channel = {}
        for line in lines:
            line = line.strip()
            if not line: continue
            
            if line.startswith('#EXTINF:'):
                current_channel = {}
                # Extract attributes
                tvg_id = re.search(r'tvg-id="([^"]*)"', line)
                tvg_name = re.search(r'tvg-name="([^"]*)"', line)
                tvg_logo = re.search(r'tvg-logo="([^"]*)"', line)
                group_title = re.search(r'group-title="([^"]*)"', line)
                
                current_channel['id'] = tvg_id.group(1) if tvg_id else ""
                current_channel['name'] = tvg_name.group(1) if tvg_name else line.split(',')[-1].strip()
                current_channel['logo'] = tvg_logo.group(1) if tvg_logo else ""
                current_channel['group'] = group_title.group(1) if group_title else ""
            elif line.startswith('http') or line.startswith('https'):
                if current_channel:
                    current_channel['url'] = line
                    channels.append(current_channel)
                    current_channel = {}

        return channels

    def save_channels(self, channels):
        # Save M3U
        m3u_content = ["#EXTM3U"]
        for c in channels:
            # Reconstruct EXTINF
            extinf = f'#EXTINF:-1 tvg-id="{c["id"]}" tvg-name="{c["name"]}" tvg-logo="{c["logo"]}" group-title="{c["group"]}",{c["name"]}'
            m3u_content.append(extinf)
            m3u_content.append(c["url"])
            
        with open(M3U_PATH, 'w') as f:
            f.write('\n'.join(m3u_content))
            
        # Save EPG
        xml_content = ['<?xml version="1.0" encoding="UTF-8"?>', '<tv>']
        
        unique_epg_channels = {}
        for c in channels:
            if c["id"] and c["id"] not in unique_epg_channels:
                unique_epg_channels[c["id"]] = c
                
        for ch_id, c in unique_epg_channels.items():
            name_esc = c["name"].replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            logo_esc = c["logo"].replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            
            xml_content.append(f'  <channel id="{ch_id}">')
            xml_content.append(f'    <display-name>{name_esc}</display-name>')
            if logo_esc:
                xml_content.append(f'    <icon src="{logo_esc}" />')
            xml_content.append('  </channel>')
            
        start_time = datetime.utcnow().strftime("%Y%m%d%H%M%S +0000")
        end_time = (datetime.utcnow() + timedelta(days=7)).strftime("%Y%m%d%H%M%S +0000")
        
        for ch_id, c in unique_epg_channels.items():
            name_esc = c["name"].replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            xml_content.append(f'  <programme start="{start_time}" stop="{end_time}" channel="{ch_id}">')
            xml_content.append(f'    <title>{name_esc} Broadcast</title>')
            xml_content.append(f'    <desc>Live Stream for {name_esc}</desc>')
            xml_content.append('  </programme>')
            
        xml_content.append('</tv>')
        
        with open(EPG_PATH, 'w') as f:
            f.write('\n'.join(xml_content))

if __name__ == "__main__":
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        print(f"Serving at port {PORT}")
        httpd.serve_forever()
