from bs4 import BeautifulSoup
import subprocess
import os

with open('ieee_conference_paper.html', 'r', encoding='utf-8') as f:
    soup = BeautifulSoup(f, 'html.parser')

svg = soup.find('svg')
if svg:
    svg['width'] = "820"
    svg['height'] = "340"
    
    html_content = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ background: #ffffff; padding: 10px; width: 840px; }}
svg {{ display: block; }}
</style>
</head>
<body>
{str(svg)}
</body>
</html>"""

    html_path = os.path.abspath('temp_svg.html')
    png_path = os.path.abspath('figure1.png')

    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html_content)

    chrome_path = r'C:\Program Files\Google\Chrome\Application\chrome.exe'
    cmd = [
        chrome_path,
        '--headless',
        '--disable-gpu',
        '--hide-scrollbars',
        '--window-size=860,380',
        f'--screenshot={png_path}',
        f'file:///{html_path.replace(os.sep, "/")}'
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    print("Return code:", res.returncode)
    print("STDOUT:", res.stdout)
    print("STDERR:", res.stderr)
    if os.path.exists(png_path):
        print('Successfully created figure1.png, size:', os.path.getsize(png_path))
    else:
        # Try msedge
        edge_path = r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'
        cmd_edge = [
            edge_path,
            '--headless',
            '--disable-gpu',
            '--hide-scrollbars',
            '--window-size=860,380',
            f'--screenshot={png_path}',
            f'file:///{html_path.replace(os.sep, "/")}'
        ]
        res_edge = subprocess.run(cmd_edge, capture_output=True, text=True)
        print("Edge Return code:", res_edge.returncode)
        print("Edge STDOUT:", res_edge.stdout)
        print("Edge STDERR:", res_edge.stderr)
        if os.path.exists(png_path):
            print('Successfully created figure1.png with Edge, size:', os.path.getsize(png_path))
