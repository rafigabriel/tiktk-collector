import json
import os
from playwright.sync_api import sync_playwright
from datetime import datetime, timezone

def unix_to_normal(unix_time, format="%Y-%m-%d %H:%M:%S"):
    return datetime.fromtimestamp(unix_time, tz=timezone.utc).strftime(format)

responses = {}  # Dicionário para armazenar vídeos sem duplicatas

def get_selected_attributes(video):
    url = generate_url_new(video)
    selected_data = {
        "nickname": video["author"]["nickname"],
        "userId": video["author"]["id"],
        "privateAccount": video["author"]["privateAccount"],
        "signature": video["author"]["signature"],
        "uniqueId": video["author"]["uniqueId"],
        "verified": video["author"]["verified"],
        "videoId": video["id"],
        "createTime": video["createTime"],
        "likesCount": video["stats"]["diggCount"],
        "shareCount": video["stats"]["shareCount"],
        "commentCount": video["stats"]["commentCount"],
        "playCount": video["stats"]["playCount"],
        "collectCount": video["stats"]["collectCount"],
        "description": video["desc"],
        "url": url,
        "timestamp": unix_to_normal(video["createTime"])
    }
    if "duration" in video["video"]:
        selected_data["duration"] = video["video"]["duration"]
    
    return selected_data

def normalize_response(response):
    videos = {}
    for item in response["itemList"]:
        video = get_selected_attributes(item)
        videos[video["videoId"]] = video
    print("Total de vídeos capturados nesta resposta:", len(videos))
    return videos

def generate_url_new(video):
    author_id = video["author"]["uniqueId"]
    video_id = video["id"]
    return f"https://www.tiktok.com/@{author_id}/video/{video_id}"

def capture_response(response):
    if "https://www.tiktok.com/api/post/item_list/" in response.url and response.status == 200:
        try:
            response_data = response.json()
            video_count = response_data['itemList'][0]['authorStats']['videoCount']
            print(f"Total de vídeos do perfil: {video_count}")
            
            response_data = normalize_response(response_data)
            responses.update(response_data)  # Adiciona os novos vídeos
            print(f"Total de vídeos coletados até agora: {len(responses)}")

        except Exception as e:
            print(f"Erro ao processar resposta: {e}")

def scroll_page(page):
    """Rola a página para carregar mais vídeos e espera tempo suficiente."""
    page.evaluate("window.scrollBy(0, window.innerHeight)")
    page.wait_for_timeout(4000)  # Aumentei para 4 segundos para garantir carregamento

def scrape(username, max_videos, output_dir):
    """ Coleta vídeos do usuário e salva os dados em JSON. """
    global responses
    responses = {}  # Limpa os vídeos antes de iniciar um novo usuário

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=False)
        page = browser.new_page()

        try:
            page.on("response", capture_response)
            page.goto(f"https://www.tiktok.com/@{username}")
            page.wait_for_load_state("networkidle")

            previous_count = 0  # Contador para verificar se novos vídeos foram carregados

            while len(responses) < max_videos:
                print(f"[{username}] Capturados {len(responses)} vídeos, rolando a página...")

                scroll_page(page)

                # Se o número de vídeos não aumentar após o scroll, interrompe o loop
                if len(responses) == previous_count:
                    print(f"[{username}] Nenhum novo vídeo encontrado após o scroll. Encerrando captura.")
                    break

                previous_count = len(responses)  # Atualiza contador

            # Salvar os dados em JSON
            user_dir = os.path.join(output_dir, username)
            os.makedirs(user_dir, exist_ok=True)
            file_path = os.path.join(user_dir, "videos.json")

            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(list(responses.values()), f, ensure_ascii=False, indent=4)

            print(f"[{username}] Captura finalizada. Total de vídeos coletados: {len(responses)}")

        except Exception as e:
            print(f"[{username}] Erro: {e}")
        finally:
            page.wait_for_timeout(5000)
            browser.close()

def process_users(user_list_file, max_videos=30, output_dir="TiktokUsersData"):
    """ Processa a lista de usuários um por um. """
    os.makedirs(output_dir, exist_ok=True)

    with open(user_list_file, "r", encoding="utf-8") as file:
        users = [line.strip() for line in file if line.strip()]

    for user in users:
        scrape(user, max_videos, output_dir)

if __name__ == "__main__":
    process_users("users.txt", max_videos=30)
