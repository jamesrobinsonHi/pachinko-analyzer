"""
パチンコ分析ツール - ローカルサーバー
P-WORLDから機種スペックを取得してフロントエンドに返す
"""
import re
import requests
from bs4 import BeautifulSoup
from flask import Flask, jsonify, request, send_from_directory

app = Flask(__name__, static_folder='.')

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36'
}

def search_machines(keyword: str) -> list[dict]:
    """P-WORLDで機種名を検索して候補リストを返す"""
    url = f'https://www.p-world.co.jp/_machine/t_machine.cgi'
    params = {'mode': '4', 'key': keyword, 'aflag': ''}
    try:
        r = requests.get(url, params=params, headers=HEADERS, timeout=10)
        r.encoding = 'euc-jp'
        soup = BeautifulSoup(r.text, 'html.parser')
        results = []
        # 機種リンク: /machine/database/{id}
        for a in soup.find_all('a', href=re.compile(r'/machine/database/\d+')):
            machine_id = re.search(r'/machine/database/(\d+)', a['href']).group(1)
            name = a.get_text(strip=True)
            if name:
                results.append({'id': machine_id, 'name': name})
        return results[:20]
    except Exception as e:
        return []

def get_machine_spec(machine_id: str) -> dict:
    """P-WORLDの機種ページからスペックを取得"""
    url = f'https://www.p-world.co.jp/machine/database/{machine_id}'
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        r.encoding = 'utf-8'
        soup = BeautifulSoup(r.content, 'html.parser')
        text = soup.get_text()

        spec = {'name': '', 'prob': None, 'balls': None, 'maker': '', 'type': ''}

        # 機種名
        h1 = soup.find('h1')
        if h1:
            spec['name'] = h1.get_text(strip=True)
        else:
            title = soup.find('title')
            if title:
                spec['name'] = title.get_text(strip=True).split('|')[0].strip()

        # 大当たり確率: 「1/xxx」パターンを探す
        prob_matches = re.findall(r'1[／/](\d+(?:\.\d+)?)', text)
        if prob_matches:
            # 最初の確率（通常確率）
            spec['prob'] = float(prob_matches[0])

        # 出玉: 「約XXXX個」「XXXX玉」パターン
        balls_matches = re.findall(r'約?(\d{3,4})(?:個|玉)', text)
        if balls_matches:
            # 最大出玉を取得
            spec['balls'] = max(int(b) for b in balls_matches)

        # メーカー
        maker_match = re.search(r'メーカー\s*[：:]\s*(.+?)[\n\r]', text)
        if maker_match:
            spec['maker'] = maker_match.group(1).strip()

        # タイプ
        type_match = re.search(r'タイプ\s*[：:]\s*(.+?)[\n\r]', text)
        if type_match:
            spec['type'] = type_match.group(1).strip()

        return spec
    except Exception as e:
        return {'error': str(e)}


@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/api/search')
def api_search():
    keyword = request.args.get('q', '').strip()
    if not keyword:
        return jsonify({'error': 'キーワードを入力してください'}), 400
    results = search_machines(keyword)
    return jsonify({'results': results})

@app.route('/api/spec/<machine_id>')
def api_spec(machine_id):
    if not re.match(r'^\d+$', machine_id):
        return jsonify({'error': '無効なIDです'}), 400
    spec = get_machine_spec(machine_id)
    return jsonify(spec)

if __name__ == '__main__':
    print('=' * 50)
    print('パチンコ分析ツール起動中...')
    print('ブラウザで http://localhost:5000 を開いてください')
    print('=' * 50)
    app.run(debug=False, port=5000)
