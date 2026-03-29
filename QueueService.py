import os
from pathlib import Path
from PDF_to_Audiobook import AudiobookConverter

QUEUE = "queue"

def remove_from_queue(srv):
    try:
        os.mkdir(QUEUE)
    except FileExistsError:
        pass

    file_number = 0

    while True:
        path = Path(os.path.join(QUEUE, str(file_number)).replace("\\", "/"))
        if not path.exists():
            file_number += 1
        else:
            with open(path, "r") as f:
                #input_file = f.readline()
                #output_file = f.readline()
                #voice = f.readline();
                all_lines_list = f.readlines()
                srv(all_lines_list[0].strip(), all_lines_list[1].strip(), all_lines_list[2].strip())
            os.remove(path)
            break

def service(input_file, output_file, voice):
    converter = AudiobookConverter()
    converter.pdf_to_audio(pdf_path=input_file, output_path=output_file, voice=voice)


if __name__ == "__main__":
    while True:
        remove_from_queue(service)
