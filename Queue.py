import os
from pathlib import Path

QUEUE = "queue"

def add_to_queue(input_file, output_file, voice):
    try:
        os.mkdir(QUEUE)
    except FileExistsError:
        pass

    file_number = 0

    while True:
        path = Path(os.path.join(QUEUE, str(file_number)).replace("\\", "/"))
        if path.exists():
            file_number += 1
        else:
            with open(path, "w") as f:
                print(input_file, file=f);
                print(output_file, file=f);
                print(voice, file=f);
            break

if __name__ == "__main__":
    add_to_queue("input_folder/HelloJesus.pdf", "output_folder/HelloJesus.mp3", "af_bella")
    add_to_queue("input_folder/HelloMichael.pdf", "output_folder/HelloMichael.mp3", "af_nicole")
    add_to_queue("input_folder/HelloWorld.pdf", "output_folder/HelloWorld.mp3", "af_sarah")
    add_to_queue("input_folder/MGMT-Product-Catalog-MGMT-Catalog-012625.pdf", "output_folder/MGMT-Product-Catalog-MGMT-Catalog-012625.wav", "af_heart")
