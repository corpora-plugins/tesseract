import sys
import os
import json
import shutil
from PIL import Image


training_dir = '/root/tesseract/tesstrain/data'
transom_dir = '/root/transom'
fonts_dir = '/usr/local/share/tessdata'
tessdata_dir = '/root/tesseract/tessdata'
tesstrain_dir = '/root/tesseract/tesstrain'


def contains(item, attrs):
    for attr in attrs:
        if attr not in item:
            return False
    return True


if len(sys.argv) >=2:
    training_file = sys.argv[1]
    training_file = f"{transom_dir}/{training_file}"
    print(f"Reading {training_file}")

    if os.path.exists(training_file):
        with open(training_file, 'r', encoding='utf-8') as training_in:
            training_set = json.load(training_in)

        if contains(training_set, ['images', 'name']) and training_set['images']:
            # Since we appear to have a valid training set, do some setting up
            model_name = training_set['name']
            ground_truth_dir = f"{training_dir}/{model_name}-ground-truth"
            base_model = training_set.get('base_model', None)

            # make sure fonts are in the correct spot
            os.makedirs(ground_truth_dir, exist_ok=True)
            fonts = [f for f in os.listdir(fonts_dir) if f.endswith('.traineddata')]
            installed_fonts = [f for f in os.listdir(tessdata_dir) if f.endswith('.traineddata')]
            for font in fonts:
                if font not in installed_fonts:
                    shutil.copy(f"{fonts_dir}/{font}", f"{tessdata_dir}/{font}")

            image_counter = 0
            for image_info in training_set['images']:
                image_file = image_info['image']
                image_file = f"{transom_dir}/{image_file}"

                if os.path.exists(image_file):
                    image = Image.open(image_file)

                    for line in image_info['lines']:
                        image_counter += 1

                        if contains(line, ['x', 'y', 'width', 'height', 'transcription']):
                            line_file_prefix = f"{ground_truth_dir}/{model_name}.exp{image_counter}"
                            line_image = image.crop((
                                line['x'],
                                line['y'],
                                line['x'] + line['width'],
                                line['y'] + line['height']
                            ))
                            line_image.save(f"{line_file_prefix}.png")

                            with open(f"{line_file_prefix}.gt.txt", 'w', encoding='utf-8') as line_out:
                                line_out.write(line['transcription'])

                    os.remove(image_file)

            if image_counter:
                start_model = ""
                if base_model:
                    start_model = f" START_MODEL={base_model}"
                command = f"make training MODEL_NAME={model_name}{start_model} TESSDATA={tessdata_dir}"
                os.chdir(tesstrain_dir)
                os.system(command)

                new_model = f"{training_dir}/{model_name}.traineddata"
                if os.path.exists(new_model):
                    shutil.move(new_model, f"{fonts_dir}/{model_name}.traineddata")

                files_to_clean = [f for f in os.listdir(training_dir) if not f == 'langdata']
                for file_to_clean in files_to_clean:
                    path_to_clean = f"{training_dir}/{file_to_clean}"
                    if os.path.isdir(path_to_clean):
                        shutil.rmtree(path_to_clean)
                    else:
                        os.remove(path_to_clean)

            os.remove(training_file)

        else:
            print("Not a valid training file!")
