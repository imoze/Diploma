import os
import json

def get_mp3_files(root_dir):
    mp3_files = []
    
    for root, dirs, files in os.walk(root_dir):
        for file in files:
            if file.lower().endswith(".mp3"):
                full_path = os.path.join(root, file)
                mp3_files.append(full_path)
    
    return mp3_files

if __name__ == "__main__":
    folder_path = r"C:\0.0.Diploma\Tracks"  # <-- укажи свою папку
    output_file = "tracks.json"

    mp3_list = get_mp3_files(folder_path)

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(mp3_list, f, indent=4, ensure_ascii=False)

    print(f"Найдено файлов: {len(mp3_list)}")
    print(f"JSON сохранён в: {output_file}")