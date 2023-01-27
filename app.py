import streamlit as st
import os
from PIL import Image
from streamlit_image_comparison import image_comparison
from moviepy.editor import *
import cv2
import re
from moviepy.video.io.VideoFileClip import VideoFileClip
import csv
import pandas as pd
import replicate
import urllib
import requests as r
import base64
import time
import shutil
import ffmpeg




def remove_existing_timing(project_name):

    df = pd.read_csv("videos/" + str(project_name) + "/timings.csv")

    df = df.drop(df.index[0:])

    df.to_csv("videos/" + str(project_name) + "/timings.csv", index=False)


def move_frame(project_name, index_of_current_item, distance_to_move, timing_details,input_video):

    print("----------------------------------------------------")
    print(project_name, index_of_current_item, distance_to_move,input_video)
    
    current_frame_number = int(calculate_frame_number_at_time(input_video, timing_details[index_of_current_item]["frame_time"], project_name))

    if distance_to_move == 0:
                        
        extract_frame(index_of_current_item, project_name, input_video, current_frame_number,timing_details)

        new_frame_number = current_frame_number

        
    
    elif distance_to_move > 0:    

        next_frame_number = int(calculate_frame_number_at_time(input_video, timing_details[index_of_current_item + 1]["frame_time"],project_name))

        abs_distance_to_move = abs(distance_to_move) / 100

        difference_between_frames = abs(next_frame_number - current_frame_number)

        new_frame_number = current_frame_number + (difference_between_frames * abs_distance_to_move)

        extract_frame(index_of_current_item, project_name, input_video, new_frame_number,timing_details)


            
    elif distance_to_move < 0:

        last_frame_number = int(calculate_frame_number_at_time(input_video, timing_details[index_of_current_item - 1]["frame_time"],project_name))

        abs_distance_to_move = abs(distance_to_move) / 100

        difference_between_frames = abs(current_frame_number - last_frame_number)

        new_frame_number = current_frame_number - (difference_between_frames * abs_distance_to_move)

        extract_frame(index_of_current_item, project_name, input_video, new_frame_number,timing_details)

    df = pd.read_csv("videos/" + str(project_name) + "/timings.csv")

    new_time = calculate_time_at_frame_number(input_video, new_frame_number, project_name)

    df.iloc[index_of_current_item, [16,1]] = [int(distance_to_move),new_time]
    
    df.to_csv("videos/" + str(project_name) + "/timings.csv", index=False)

        
            

def get_app_settings():

    app_settings = {}

    with open("app_settings.csv") as f:

        lines = [line.split(',') for line in f.read().splitlines()]

    for i in range(1, 4):

        app_settings[lines[i][0]] = lines[i][1]

    return app_settings

def get_project_settings(project_name):

    project_settings = {}

    with open("videos/" + str(project_name)  + "/settings.csv") as f:

        lines = [line.split(',') for line in f.read().splitlines()]

    for i in range(1, 7):

        project_settings[lines[i][0]] = lines[i][1]

    return project_settings


def get_model_details(model_name):

    with open('models.csv', 'r') as f:
        reader = csv.reader(f)
        for row in reader:
            if row[0] == model_name:
                model_details = {
                    'name': row[0],
                    'id': row[1],
                    'keyword': row[2],
                    'training_images': row[3],
                }
                return model_details


def create_working_assets(video_name):

    os.mkdir("videos/" + video_name + "/assets")

    os.mkdir("videos/" + video_name + "/assets/frames")

    os.mkdir("videos/" + video_name + "/assets/frames/1_selected")
    os.mkdir("videos/" + video_name + "/assets/frames/2_character_pipeline_completed")
    os.mkdir("videos/" + video_name + "/assets/frames/3_backdrop_pipeline_completed")

    os.mkdir("videos/" + video_name + "/assets/resources")

    os.mkdir("videos/" + video_name + "/assets/resources/backgrounds")
    os.mkdir("videos/" + video_name + "/assets/resources/masks")
    os.mkdir("videos/" + video_name + "/assets/resources/music")
    os.mkdir("videos/" + video_name + "/assets/resources/training_data")
    os.mkdir("videos/" + video_name + "/assets/resources/input_videos")

    os.mkdir("videos/" + video_name + "/assets/videos")

    os.mkdir("videos/" + video_name + "/assets/videos/0_raw")
    os.mkdir("videos/" + video_name + "/assets/videos/1_final")

    data = {'key': ['number_of_interpolation_steps', 'what_to_append_to_each_prompt','base_prompt','song', 'input_type', 'input_video'],
        'value': ['', '', '','', '', '']}

    df = pd.DataFrame(data)

    df.to_csv(f'videos/{video_name}/settings.csv', index=False)

    df = pd.DataFrame(columns=['index_number','time','frame_number','primary_image','alt_image_1','alt_image_2','alt_image_3','alt_image_4','alt_image_5','alt_image_6','model','prompt','notes','ending_frame','interpolation_style','strength','frame_adjustment'])

    df.loc[0] = [1, 0, 0, '', '', '', '', '', '', '', '', '', '', '', '','']

    df.to_csv(f'videos/{video_name}/timings.csv', index=False)

def update_project_setting(key, pair_value, project_name):
    
    csv_file_path = f'videos/{project_name}/settings.csv'
    
    with open(csv_file_path, 'r') as csv_file:

        csv_reader = csv.reader(csv_file)

        rows = []

        for row in csv_reader:
            if row[0] == key:            
                row_number = csv_reader.line_num - 2            
                new_value = pair_value        
    
    df = pd.read_csv(csv_file_path)

    df.iat[row_number, 1] = new_value

    df.to_csv(csv_file_path, index=False)

def prompt_interpolation_model(img1, img2, video_name, video_number, interpolation_steps, replicate_api_key):

    os.environ["REPLICATE_API_TOKEN"] = replicate_api_key

    model = replicate.models.get("google-research/frame-interpolation")

    output = model.predict(frame1=open(img1, "rb"), frame2=open(
        img2, "rb"), times_to_interpolate=interpolation_steps)

    video_name = "videos/" + video_name + \
        "/assets/videos/0_raw/" + str(video_number) + ".mp4"

    try:

        urllib.request.urlretrieve(output, video_name)

    except Exception as e:

        print(e)

    clip = VideoFileClip(video_name)

def get_timing_details(video_name):

    timing_details = []

    with open(("videos/" + str(video_name) + "/timings.csv"), 'r') as f:

        lines = [line.split(',') for line in f.read().splitlines()]

    number_of_rows = (len)(lines)


    for i in range(1, number_of_rows):        

        current_frame = {}

        current_frame["frame_time"] = lines[i][1]

        if current_frame["frame_time"] != "":
            
            current_frame["frame_number"] = lines[i][2]
            current_frame["primary_image"] = lines[i][3]
            current_frame["alt_image_1"] = lines[i][4]
            current_frame["alt_image_2"] = lines[i][5]
            current_frame["alt_image_3"] = lines[i][6]
            current_frame["alt_image_4"] = lines[i][7]
            current_frame["alt_image_5"] = lines[i][8]
            current_frame["alt_image_6"] = lines[i][9]
            current_frame["model_id"] = lines[i][10]            
            current_frame["notes"] = lines[i][12]
            current_frame["interpolation_style"] = lines[i][13]
            current_frame["strength"] = lines[i][11]
            current_frame["prompt"] = lines[i][15]        

            timing_details.append(current_frame)

    return timing_details

def calculate_time_at_frame_number(input_video, frame_number, project_name):

    input_video = "videos/" + str(project_name) + "/assets/resources/input_videos/" + str(input_video)

    video = cv2.VideoCapture(input_video)

    frame_count = float(video.get(cv2.CAP_PROP_FRAME_COUNT))

    frame_percentage = float(frame_number / frame_count)

    fps = int(video.get(cv2.CAP_PROP_FPS))

    length_of_video = float(frame_count / fps)

    time_at_frame = float(frame_percentage * length_of_video)

    return time_at_frame

def calculate_frame_number_at_time(input_video, time_of_frame, project_name):

    time_of_frame = float(time_of_frame)

    input_video = "videos/" + str(project_name) + "/assets/resources/input_videos/" + str(input_video)

    video = cv2.VideoCapture(input_video)

    frame_count = float(video.get(cv2.CAP_PROP_FRAME_COUNT))

    fps = int(video.get(cv2.CAP_PROP_FPS))

    length_of_video = float(frame_count / fps)

    percentage_of_video = float(time_of_frame / length_of_video)

    frame_number = int(percentage_of_video * frame_count)

    if frame_number == 0:
        frame_number = 1

    return frame_number



def extract_all_frames(input_video, project_name, timing_details, time_per_frame):

    folder = 'videos/' + str(project_name) + '/assets/frames/1_selected'

    for filename in os.listdir(folder):
        os.remove(os.path.join(folder, filename))

    timing_details = get_timing_details(project_name)

    for i in timing_details:

        index_of_current_item = timing_details.index(i)
    
        time_of_frame = float(timing_details[index_of_current_item]["frame_time"])

        extract_frame_number = calculate_frame_number_at_time(input_video, time_of_frame, project_name)

        extract_frame(index_of_current_item, project_name, input_video, extract_frame_number,timing_details)

def extract_frame(frame_number, video_name, input_video, extract_frame_number,timing_details):

    input_video = "videos/" + str(video_name) + "/assets/resources/input_videos/" + str(input_video)

    input_video = cv2.VideoCapture(input_video)

    total_frames = input_video.get(cv2.CAP_PROP_FRAME_COUNT)

    if extract_frame_number == total_frames:

        extract_frame_number = int(total_frames - 1)

    input_video.set(cv2.CAP_PROP_POS_FRAMES, extract_frame_number)

    ret, frame = input_video.read()

    df = pd.read_csv("videos/" + str(video_name) + "/timings.csv")

    if timing_details[frame_number]["frame_number"] == "":
    
        df.iloc[frame_number, [2]] = [extract_frame_number]

    df.to_csv("videos/" + str(video_name) + "/timings.csv", index=False)

    cv2.imwrite("videos/" + video_name + "/assets/frames/1_selected/" + str(frame_number) + ".png", frame)

    img = Image.open("videos/" + video_name + "/assets/frames/1_selected/" + str(frame_number) + ".png")

    img.save("videos/" + video_name + "/assets/frames/1_selected/" + str(frame_number) + ".png")

    return str(frame_number) + ".png"


def touch_up_images(video_name, replicate_api_key, index_of_current_item):

    os.environ["REPLICATE_API_TOKEN"] = replicate_api_key

    model = replicate.models.get("tencentarc/gfpgan")

    image = "videos/" + str(video_name) + "/assets/frames/2_character_pipeline_completed/" + str(index_of_current_item) + ".png"

    output = model.predict(img=open(image, "rb"))

    try:

        urllib.request.urlretrieve(output, image)

    except Exception as e:

        print("Error in touching up image: " + str(e))

def resize_image(video_name, image_number, new_width,new_height):

    image = Image.open("videos/" + str(video_name) + "/assets/frames/2_character_pipeline_completed/" + str(image_number) + ".png")

    resized_image = image.resize((new_width, new_height))

    resized_image.save("videos/" + str(video_name) + "/assets/frames/2_character_pipeline_completed/" + str(image_number) + ".png")

    return resized_image

def face_swap(replicate_api_key, video_name, index_of_current_item,stablediffusionapi_com_api_key):
    
    os.environ["REPLICATE_API_TOKEN"] = replicate_api_key

    model = replicate.models.get("arielreplicate/ghost_face_swap")

    version = model.versions.get("106df0aaf9690354379d8cd291ad337f6b3ea02fe07d90feb1dafd64820066fa")

    source_face = upload_image("videos/" + str(video_name) + "/face.png")

    target_face = upload_image("videos/" + str(video_name) + "/assets/frames/1_selected/" + str(index_of_current_item) + ".png")

    output = version.predict(source_path=source_face, target_path=target_face,use_sr=0)

    new_image = "videos/" + str(video_name) + "/assets/frames/2_character_pipeline_completed/" + str(index_of_current_item) + ".png"
    
    try:

        urllib.request.urlretrieve(output, new_image)

    except Exception as e:

        print(e)

def prompt_model_stability(videoname, image_number, prompt, dreamstudio_ai_api_key):

    print("YOU NEED TO FIX BASIC PROMPTING!!!!!!")


def delete_frame(video_name, image_number):

    os.remove("videos/" + str(video_name) + "/assets/frames/1_selected/" + str(image_number) + ".png")

    df = pd.read_csv("videos/" + str(video_name) + "/timings.csv")

    


    for i in range(int(image_number)+1, len(os.listdir("videos/" + str(video_name) + "/assets/frames/1_selected"))+1):
            
        os.rename("videos/" + str(video_name) + "/assets/frames/1_selected/" + str(i) + ".png", "videos/" + str(video_name) + "/assets/frames/1_selected/" + str(i - 1) + ".png")

        df.iloc[i, [0]] = str(i - 1)

    # remove the row from the timings.csv file using pandas

    df = df.drop([int(image_number)])

    df.to_csv("videos/" + str(video_name) + "/timings.csv", index=False)

    

    







def prompt_model_dreambooth(strength, folder_name,video_name, image_number, init_image, prompt, model_id, sd_api_key):


    sd_url = "https://stablediffusionapi.com/api/v4/dreambooth/img2img"

    init_image = upload_image("videos/" + str(video_name) + "/assets/frames/" + str(folder_name) + "/" + str(image_number) + ".png")
        
    payload = {
        "key": sd_api_key,
        "prompt": str(prompt),
        "width": "720",
        "height": "480",
        "samples": "1",
        "num_inference_steps": "20",
        "seed": "0",
        "guidance_scale": "7",
        "webhook": "0",
        "strength": strength,
        "track_id": "null",
        "init_image": init_image,
        "model_id": model_id

    }

    print(payload)

    completed = "false"

    response = r.post(sd_url, json=payload)

    while completed == "false":

        if response.json()["status"] == "processing":

            wait = int(response.json()["eta"])

            print("Processing, ETA: " + str(wait) + " seconds")

            time.sleep(wait)

            response = "https://stablediffusionapi.com/api/v3/dreambooth/fetch/" + str(response.json()["id"])

        elif response.json()["status"] == "success":

            time.sleep(3)

            output_url = response.json()["output"][0]

            image = r.get(output_url)

            with open("videos/" + str(video_name) + "/assets/frames/" + str(folder_name) + "/"+ str(image_number)+".png", "wb") as f:

                f.write(image.content)

            completed = "true"

        else:

            print("Something went wrong, trying again in 30 seconds.")

            print(response)

            time.sleep(30)

    return completed


def upload_image(image_location):

    upload_success = "false"

    upload_attempts = 0

    while upload_success == "false":

        sd_api_key = "JH5O46WRabTIbn11Q9xOcKXucoMuGsMbvrctrbE6Zsc6ANtrHwhXWOob5pAy"

        sd_url = "https://stablediffusionapi.com/api/v3/base64_crop"

        # resize_image(video_name,image_number, 720, 480)

        with open(image_location, "rb") as image_file:

            image_bytes = image_file.read()

        encoded_string = base64.b64encode(image_bytes)

        upload_string = "data:image/png;base64," + \
            encoded_string.decode("utf-8").replace(" ", "")

        payload = {
            "key": sd_api_key,
            "image": upload_string,
            "crop": "false"
        }

        response = r.post(sd_url, json=payload)

        if response.json()["status"] == "success":

            upload_success = "true"    

            return response.json()["link"]

        else:

            time.sleep(30)

            print(response.text)

def update_slice_of_video_speed(video_name, input_video, desired_speed_change):

    clip = VideoFileClip("videos/" + str(video_name) +
                         "/assets/videos/0_raw/" + str(input_video))

    clip_location = "videos/" + \
        str(video_name) + "/assets/videos/0_raw/" + str(input_video)

    desired_speed_change_text = str(desired_speed_change) + "*PTS"

    video_stream = ffmpeg.input(str(clip_location))

    video_stream = video_stream.filter('setpts', desired_speed_change_text)

    ffmpeg.output(video_stream, "videos/" + str(video_name) +
                  "/assets/videos/0_raw/output_" + str(input_video)).run()

    video_capture = cv2.VideoCapture(
        "videos/" + str(video_name) + "/assets/videos/0_raw/output_" + str(input_video))

    os.remove("videos/" + str(video_name) +
              "/assets/videos/0_raw/" + str(input_video))
    os.rename("videos/" + str(video_name) + "/assets/videos/0_raw/output_" + str(input_video),
              "videos/" + str(video_name) + "/assets/videos/0_raw/" + str(input_video))

def slice_part_of_video(video_name, video_number, video_start_percentage, video_end_percentage, slice_name):

    input_video = "videos/" + \
        str(video_name) + "/assets/videos/0_raw/" + str(video_number) + ".mp4"

    video_capture = cv2.VideoCapture(input_video)

    frame_rate = video_capture.get(cv2.CAP_PROP_FPS)

    total_duration_of_clip = video_capture.get(
        cv2.CAP_PROP_FRAME_COUNT) / frame_rate

    start_time = float(video_start_percentage) * float(total_duration_of_clip)

    end_time = float(video_end_percentage) * float(total_duration_of_clip)

    clip = VideoFileClip(input_video).subclip(
        t_start=start_time, t_end=end_time)

    output_video = "videos/" + \
        str(video_name) + "/assets/videos/0_raw/" + str(slice_name) + ".mp4"

    clip.write_videofile(output_video, audio=False)

def update_video_speed(video_name, video_number, duration_of_static_time, total_duration_of_clip):

    input_video = "videos/" + \
        str(video_name) + "/assets/videos/0_raw/" + str(video_number) + ".mp4"

    slice_part_of_video(video_name, video_number, 0, .1, "static")

    slice_part_of_video(video_name, video_number, 0, 1, "moving")

    video_capture = cv2.VideoCapture(
        "videos/" + str(video_name) + "/assets/videos/0_raw/static.mp4")

    frame_rate = video_capture.get(cv2.CAP_PROP_FPS)

    total_duration_of_static = video_capture.get(
        cv2.CAP_PROP_FRAME_COUNT) / frame_rate

    desired_speed_change_of_static = float(
        duration_of_static_time) / float(total_duration_of_static)

    update_slice_of_video_speed(
        video_name, "static.mp4", desired_speed_change_of_static)

    video_capture = cv2.VideoCapture(
        "videos/" + str(video_name) + "/assets/videos/0_raw/moving.mp4")

    frame_rate = video_capture.get(cv2.CAP_PROP_FPS)

    total_duration_of_moving = video_capture.get(
        cv2.CAP_PROP_FRAME_COUNT) / frame_rate

    total_duration_of_moving = float(total_duration_of_moving)

    total_duration_of_clip = float(total_duration_of_clip)

    duration_of_static_time = float(duration_of_static_time)

    desired_speed_change_of_moving = (
        total_duration_of_clip - duration_of_static_time) / total_duration_of_moving

    update_slice_of_video_speed(
        video_name, "moving.mp4", desired_speed_change_of_moving)

    final_clip = concatenate_videoclips([VideoFileClip("videos/" + str(video_name) + "/assets/videos/0_raw/static.mp4"),
                                        VideoFileClip("videos/" + str(video_name) + "/assets/videos/0_raw/moving.mp4")])

    final_clip.write_videofile(
        "videos/" + str(video_name) + "/assets/videos/0_raw/full_output.mp4", fps=30)

    os.remove("videos/" + str(video_name) + "/assets/videos/0_raw/moving.mp4")
    os.remove("videos/" + str(video_name) + "/assets/videos/0_raw/static.mp4")
    os.rename("videos/" + str(video_name) + "/assets/videos/0_raw/full_output.mp4",
              "videos/" + str(video_name) + "/assets/videos/1_final/" + str(video_number) + ".mp4")

def calculate_desired_duration_of_each_clip(timing_details):

    number_of_items = len(timing_details)

    for i in range(0, number_of_items):

        index_of_item = i
        length_of_list = len(timing_details)

        if index_of_item == (length_of_list - 1):

            time_of_frame = timing_details[index_of_item]["frame_time"]

            duration_of_static_time = 0.2

            end_duration_of_frame = float(
                time_of_frame) + float(duration_of_static_time)

            total_duration_of_frame = float(
                end_duration_of_frame) - float(time_of_frame)

        else:

            time_of_frame = timing_details[index_of_item]["frame_time"]

            time_of_next_frame = timing_details[index_of_item +
                                                1]["frame_time"]

            total_duration_of_frame = float(
                time_of_next_frame) - float(time_of_frame)

        duration_of_static_time = 0.2

        duration_of_morph = float(
            total_duration_of_frame) - float(duration_of_static_time)

        timing_details[index_of_item]["total_duration_of_clip"] = total_duration_of_frame

        timing_details[index_of_item]["duration_of_morph_time"] = duration_of_morph

        timing_details[index_of_item]["duration_of_static_time"] = duration_of_static_time

    return timing_details

def hair_swap(replicate_api_key, video_name, index_of_current_item,stablediffusionapi_com_api_key):

    os.environ["REPLICATE_API_TOKEN"] = replicate_api_key

    model = replicate.models.get("cjwbw/style-your-hair")

    version = model.versions.get("c4c7e5a657e2e1abccd57625093522a9928edeccee77e3f55d57c664bcd96fa2")

    source_hair = upload_image("videos/" + str(video_name) + "/face.png", stablediffusionapi_com_api_key)

    target_hair = upload_image("videos/" + str(video_name) + "/assets/frames/2_character_pipeline_completed/" + str(index_of_current_item) + ".png")

    output = version.predict(source_image=source_hair, target_image=target_hair)

    new_image = "videos/" + str(video_name) + "/assets/frames/2_character_pipeline_completed/" + str(index_of_current_item) + ".png"

    try:

        urllib.request.urlretrieve(output, new_image)

    except Exception as e:

        print(e)

def prompt_model_depth2img(strength,video_name, image_number, replicate_api_key, timing_details):

    
    os.environ["REPLICATE_API_TOKEN"] = replicate_api_key

    prompt = timing_details[image_number]["prompt"]

    print(prompt)

    model = replicate.models.get("jagilley/stable-diffusion-depth2img")

    version = model.versions.get("68f699d395bc7c17008283a7cef6d92edc832d8dc59eb41a6cafec7fc70b85bc")

    image = f"videos/{video_name}/assets/frames/1_selected/{image_number}.png"

    image = upload_image(image)

    output = version.predict(input_image=image, prompt_strength=str(strength), prompt=prompt, negative_prompt = "writing, text")

    new_image = "videos/" + str(video_name) + "/assets/frames/2_character_pipeline_completed/" + str(image_number) + ".png"
    
    try:

        urllib.request.urlretrieve(output[0], new_image)

    except Exception as e:

        print(e)


def restyle_images(strength, folder_name,video_name, frame_number, prompt, model_id, stablediffusionapi_com_api_key, dreamstudio_ai_api_key,replicate_api_key, timing_details):

    if model_id == "sd":
        prompt_model_stability(strength, folder_name,video_name, frame_number,prompt, dreamstudio_ai_api_key)

    elif model_id == "depth2img":
        prompt_model_depth2img(strength,video_name, frame_number,replicate_api_key, timing_details)


    else:
        prompt_model_dreambooth(strength, folder_name,video_name, frame_number, str(frame_number) + ".png", timing_details, model_id, stablediffusionapi_com_api_key)



def character_pipeline(index_of_current_item, project_name, app_settings, project_settings, timing_details):


    if timing_details[index_of_current_item]["model_id"] != "depth2img":

        face_swap(app_settings["replicate_com_api_key"], project_name, index_of_current_item, app_settings["stablediffusionapi_com_api_key"])

        touch_up_images(project_name, app_settings["replicate_com_api_key"], index_of_current_item)

        resize_image(project_name, index_of_current_item, 704,512)

    # hair_swap(key_settings["replicate_com_api_key"],video_name,index_of_current_item,key_settings["stablediffusionapi_com_api_key"])

    # INSERT CLOTHES SWAP

    restyle_images(timing_details[index_of_current_item]["strength"],"2_character_pipeline_completed",project_name, index_of_current_item, timing_details[index_of_current_item]["prompt"], timing_details[index_of_current_item]["model_id"], app_settings["stablediffusionapi_com_api_key"], app_settings["dreamstudio_ai_api_key"],app_settings["replicate_com_api_key"],timing_details)


def get_models():

    df = pd.read_csv('models.csv')

    models = df[df.columns[0]].tolist()

    return models


def update_timing_values(project_name, index_of_current_item,prompt, strength, model):

    df = pd.read_csv("videos/" + str(project_name) + "/timings.csv")

    df.iloc[index_of_current_item, [15,11,10]] = [prompt,strength,model]
    
    df.to_csv("videos/" + str(project_name) + "/timings.csv", index=False)


def main():

    app_settings = get_app_settings()

    if 'stage' not in st.session_state:
        st.session_state['stage'] = ''

    header1, header2 = st.sidebar.columns([3, 1])

    header1.title("Banodoco")
    header2.button("Settings")

        
    project_name = "eyebrow_demo"
    project_name = st.sidebar.selectbox("Select an option", os.listdir("videos"),index=3)
    

    if project_name == "":

        st.write("No projects found")

    else:

        #key_settings = get_key_settings("videos/" + str(project_name) + "/settings.csv")

        if not os.path.exists("videos/" + project_name + "/assets"):

            create_working_assets(project_name)

        timing_details = get_timing_details(project_name)


        st.session_state.stage = st.sidebar.radio("Select an option",
                                    ["Project Settings",
                                    "Train Model",
                                    "Key Frame Selection",
                                    "Background Replacement",
                                    "Frame Styling",
                                    "Frame Interpolation",
                                    "Video Rendering"])

        st.header(st.session_state.stage)
        
        if st.session_state.stage == "Key Frame Selection":

            timing_details = get_timing_details(project_name)

            images_list = [f for f in os.listdir(f'videos/{project_name}/assets/frames/0_extracted') if f.endswith('.png')]
    
            images_list.sort(key=lambda f: int(re.sub('\D', '', f)))

            st.sidebar.subheader("Extract key frames from video")

            granularity = st.sidebar.slider("Choose frame granularity", min_value=5, max_value=50, step=5, value = 10)

            input_video_list = [f for f in os.listdir(f'videos/{project_name}/assets/resources/input_videos') if f.endswith('.mp4')]                
                
            input_video = st.sidebar.selectbox("Input video:", input_video_list)

            input_video_cv2 = cv2.VideoCapture(f'videos/{project_name}/assets/resources/input_videos/{input_video}')

            total_frames = input_video_cv2.get(cv2.CAP_PROP_FRAME_COUNT)

            fps = input_video_cv2.get(cv2.CAP_PROP_FPS)
    
            if st.sidebar.checkbox("I understand that running this will remove all existing frames"):

                if st.sidebar.button("Update granularity"):

                    remove_existing_timing(project_name)

                    # remove all .pngs from 0_extracted

                    for f in os.listdir(f'videos/{project_name}/assets/frames/0_extracted'):
                        os.remove(f'videos/{project_name}/assets/frames/0_extracted/{f}')
                    
                    for i in range(0, int(input_video_cv2.get(cv2.CAP_PROP_FRAME_COUNT)), int(granularity)):

                        input_video_cv2.set(cv2.CAP_PROP_POS_FRAMES, i)

                        ret, frame = input_video_cv2.read()

                        cv2.imwrite(f"videos/{project_name}/assets/frames/0_extracted/" + str(i) + ".png", frame)

                        st.session_state['select_frames'] = []

                    cv2.imwrite(f"videos/{project_name}/assets/frames/0_extracted/" + str(int(float(total_frames))) + ".png", int(float(total_frames)))

                    st.experimental_rerun()
            else:
                st.sidebar.button("Update granularity", disabled=True)

            st.sidebar.write(f"This video is {total_frames} frames long and has a framerate of {fps} fps.")

            st.sidebar.video(f'videos/{project_name}/assets/resources/input_videos/{input_video}')

            timing_details = get_timing_details(project_name)

            if len(timing_details) == 0:

                st.header("<------- Extract Frames To Select From Here")
                    
            else:
                            
                for image_name in timing_details:

                    index_of_current_item = timing_details.index(image_name)
                
                    image = Image.open(f'videos/{project_name}/assets/frames/1_selected/{index_of_current_item}.png')            
                    st.subheader(f'Image Name: {index_of_current_item}')                
                    st.image(image, use_column_width=True)
                    
                    col1, col2,col3 = st.columns([2,1,1])

                    current_item =  str(index_of_current_item) + "_lad"

                    
                    with col1:

                       st.write(timing_details[index_of_current_item]["frame_time"])
                

                    with col2:

                        delete_confirmed = 'false'

                        if st.checkbox(f"Confirm you want to delete {index_of_current_item}"):
                            delete_confirmed = 'true'
                            

                    with col3:

                        if delete_confirmed == 'true':
                            if st.button(f"Delete {index_of_current_item} Frame", disabled=False):
                                delete_frame(project_name, index_of_current_item)
                                st.experimental_rerun()

                        else: 
                            st.button(f"Delete {index_of_current_item} Frame", type="secondary", disabled=True)


            st.title('Add key frames to your project')

            st.write("Select a frame from the slider below and click 'Add Frame' it to the end of your project")

            images = os.listdir(f"videos/{project_name}/assets/frames/0_extracted")

            # remove .png from the file name

            images = [i.replace(".png", "") for i in images]

            images.sort(key=lambda f: int(''.join(filter(str.isdigit, f))))

            # extract the name of the seond item in the list
            #granularity = int(images[1])

            if timing_details == []:
                min_frames = 0
            else:
                length_of_timing_details = len(timing_details) - 1
                print(timing_details[length_of_timing_details])
                print(len(timing_details))
                print(timing_details[length_of_timing_details]["frame_number"])
                min_frames= int(float(timing_details[length_of_timing_details]["frame_number"]))

            # make max_frames equal to the number that's multiplied by the granularity
            max_frames = int((float(total_frames) / float(granularity))) * int(granularity)
    
            slider = st.slider("Choose Frame", max_value= min_frames+ 100, min_value=min_frames,step=granularity, value = min_frames + granularity)



            st.image(f"videos/{project_name}/assets/frames/0_extracted/{slider}.png")

            if st.button(f"Add Frame {slider} to Project"):     

                frame_time = calculate_time_at_frame_number(input_video, float(slider),project_name)

                df = pd.read_csv(f'videos/{project_name}/timings.csv')

                # find the legnth of timing_details + 1

                last_index = len(timing_details)

                new_row = {'index_number': last_index, 'frame_time': frame_time, 'frame_number': slider}

                df.loc[last_index] = new_row

                df.to_csv(f'videos/{project_name}/timings.csv', index=False)

                # copy the file called slider .png from 0_extracted to the folder called 1_selected and name it last_index.png

                shutil.copy(f"videos/{project_name}/assets/frames/0_extracted/{slider}.png", f"videos/{project_name}/assets/frames/1_selected/{last_index}.png")


                

                st.experimental_rerun()




    



        elif st.session_state.stage == "Background Replacement":
                      
            images_list = [f for f in os.listdir(f'videos/{project_name}/assets/frames/1_selected') if f.endswith('.png')]

            images_list = sorted(images_list)

            images_list.sort(key=lambda f: int(re.sub('\D', '', f)))
            
            background_list = os.listdir(f'videos/{project_name}/assets/resources/backgrounds')
            
            st.sidebar.header("Batch background replacement")

            range_start = st.sidebar.slider('Update From', 0, len(images_list), 1)

            range_end = st.sidebar.slider('Update To', 0, len(images_list), 1)

            background_image = st.sidebar.selectbox("Range background", background_list)

            st.sidebar.image(f"videos/{project_name}/assets/resources/backgrounds/{background_image}", use_column_width=True)

            if range_start <= range_end:

                if st.sidebar.button(f'Swap background'):

                    for i in range(range_start, range_end):
                        swap_background()

            else:
                    
                    st.sidebar.write("Select a valid range")

            uploaded_files = st.sidebar.file_uploader("Add more background images here", accept_multiple_files=True)
            if uploaded_files is not None:
                for uploaded_file in uploaded_files:
                    file_details = {"FileName":uploaded_file.name,"FileType":uploaded_file.type}
                    st.write(file_details)
                    img = Image.open(uploaded_file)        
                    with open(os.path.join(f"videos/{project_name}/assets/resources/backgrounds",uploaded_file.name),"wb") as f: 
                        f.write(uploaded_file.getbuffer())         
                        st.success("Saved File") 
                        # apend the image to the list
                        images_list.append(uploaded_file.name)
            

            for image_name in images_list:
            
                image = Image.open(f'videos/{project_name}/assets/frames/1_selected/{image_name}')            
            
                st.subheader(f'{image_name}')                

                st.image(image, use_column_width=True)
                                        


       
        elif st.session_state.stage == "Frame Styling":

            timing_details = get_timing_details(project_name)
    
            project_settings = get_project_settings(project_name)

            images_list = [f for f in os.listdir(f'videos/{project_name}/assets/frames/2_character_pipeline_completed') if f.endswith('.png')]
    
            images_list.sort(key=lambda f: int(re.sub('\D', '', f)))

            if len(images_list) == 0:
                st.write("<------- Restyle Frames Here")

            st.sidebar.header("Restyle Frames")

            restyle1, restyle2, restyle3 = st.sidebar.tabs(["Character Restyling", "Scene Restyling", "Image Editing"])

            with restyle1:
                
                prompt = st.sidebar.text_area(f"Prompt", value=project_settings["base_prompt"], label_visibility="visible")

                strength = st.sidebar.number_input(f"Batch strength", value =0.25)

                models = get_models()

                models.append('sd')

                model = st.sidebar.selectbox(f"Model", models)
                
                if model != "sd":

                    model_details = get_model_details(model)

                    st.sidebar.write(f"Must include '{model_details['keyword']}' in the prompt when running this model")

                range_start = st.sidebar.slider('Update From', 0, len(timing_details) -1, 0)

                range_end = st.sidebar.slider('Update To', 0, len(timing_details) - 1, 1)


                range_end = range_end + 1

                project_settings = get_project_settings(project_name)

                app_settings = get_app_settings()

                if 'restyle_button' not in st.session_state:
                    st.session_state['restyle_button'] = ''
                    st.session_state['item_to_restyle'] = ''


                if range_start <= range_end:

                    if st.sidebar.button(f'Batch restyle') or st.session_state['restyle_button'] == 'yes':

                        if st.session_state['restyle_button'] == 'yes':
                            range_start = int(st.session_state['item_to_restyle'])
                            range_end = range_start + 1
                            st.session_state['restyle_button'] = ''
                            st.session_state['item_to_restyle'] = ''

                        for i in range(range_start, range_end): 
                                                

                            index_of_current_item = i
                            get_model_details(model)                
                            update_timing_values(project_name, index_of_current_item, prompt, strength, model_details['id'])                                                    
                            timing_details = get_timing_details(project_name)
                            character_pipeline(index_of_current_item, project_name, app_settings, project_settings, timing_details)
                                                    

                        st.experimental_rerun()

                else:
                        
                        st.sidebar.write("Select a valid range")

            with restyle2:

                st.sidebar.write("Scene Restyling")

            with restyle3:
                
                st.sidebar.write("Image Editing")
        
            for i in timing_details:

                # set image number to the current image number                
                index_of_current_item = timing_details.index(i)
                image_name = str(timing_details.index(i)) + ".png"
                            
                image = Image.open(f'videos/{project_name}/assets/frames/1_selected/{index_of_current_item}.png')            
                st.subheader(f'Image #: {index_of_current_item}') 
                if os.path.exists(f'videos/{project_name}/assets/frames/2_character_pipeline_completed/{index_of_current_item}.png'):
                    img2=f'videos/{project_name}/assets/frames/2_character_pipeline_completed/{index_of_current_item}.png'
                else:
                    img2='https://i.ibb.co/GHVfjP0/Image-Not-Yet-Created.png'          
                image_comparison(starting_position=10,
                    img1=f'videos/{project_name}/assets/frames/1_selected/{index_of_current_item}.png',
                    img2=img2)


                col1, col2, col3, col4 = st.columns(4)

                with col1:

                    if st.button("Generate New Variations", key=f"new_variations_{index_of_current_item}"):
                        st.session_state['restyle_button'] = 'yes'
                        st.session_state['item_to_restyle'] = index_of_current_item                        
                        st.experimental_rerun()

                with col2:

                    st.button("<- Previous Variaton", key=f"previous_variation_{index_of_current_item}", disabled=True)

                with col3:
                        
                    st.button("Next Variation ->", key=f"next_variation_{index_of_current_item}")

                with col4:

                    st.button("Promote Current Variation", key=f"prompte_current_{index_of_current_item}", disabled=True)




        elif st.session_state.stage == "Frame Interpolation":
            st.write("This is the frame interpolation view")
            timing_details = get_timing_details(project_name)
            key_settings = get_app_settings()
            total_number_of_videos = len(timing_details) - 1

            interpolation_steps = st.slider("Number of interpolation steps", min_value=1, max_value=8, value=4)

            if st.button("Interpolate Videos"):
                for i in timing_details:

                    index_of_current_item = timing_details.index(i)

                    if index_of_current_item <= total_number_of_videos:

                        if not os.path.exists("videos/" + str(project_name) + "/assets/videos/0_raw/" + str(index_of_current_item) + ".mp4"):

                            if total_number_of_videos == index_of_current_item:

                                current_image_location = "videos/" + str(project_name) + "/assets/frames/2_character_pipeline_completed/" + str(index_of_current_item) + ".png"

                                final_image_location = "videos/" + str(project_name) + "/assets/frames/2_character_pipeline_completed/" + str(key_settings["ending_image"])

                                prompt_interpolation_model(current_image_location, final_image_location, project_name, index_of_current_item,
                                                        interpolation_steps, key_settings["replicate_com_api_key"])

                            else:

                                current_image_location = "videos/" + str(project_name) + "/assets/frames/2_character_pipeline_completed/" + str(index_of_current_item) + ".png"

                                next_image_location = "videos/" + str(project_name) + "/assets/frames/2_character_pipeline_completed/" + str(index_of_current_item+1) + ".png"

                                prompt_interpolation_model(current_image_location, next_image_location, project_name, index_of_current_item,
                                                        interpolation_steps, key_settings["replicate_com_api_key"])

          

               


        elif st.session_state.stage == "Video Rendering":
            final_video_name = st.text_input("What would you like to name this video?")

            if st.button("Render Video"):
                timing_details = get_timing_details(project_name)
                total_number_of_videos = len(timing_details) - 1
                timing_details = calculate_desired_duration_of_each_clip(timing_details)

                for i in timing_details:

                    index_of_current_item = timing_details.index(i)

                    if index_of_current_item <= total_number_of_videos:

                        if not os.path.exists("videos/" + str(project_name) + "/assets/videos/1_final/" + str(index_of_current_item) + ".mp4"):

                            total_duration_of_clip = timing_details[index_of_current_item]['total_duration_of_clip']

                            total_duration_of_clip = float(total_duration_of_clip)

                            if index_of_current_item == total_number_of_videos:

                                total_duration_of_clip = timing_details[index_of_current_item]['total_duration_of_clip']
                                duration_of_static_time = 0.2
                                duration_of_static_time = float(
                                    duration_of_static_time) / 2

                            elif index_of_current_item == 0:

                                duration_of_static_time = 0

                            else:

                                duration_of_static_time = 0.2

                                duration_of_static_time = float(
                                    duration_of_static_time)

                            update_video_speed(project_name, index_of_current_item, duration_of_static_time, total_duration_of_clip)

                video_list = []

                for i in timing_details:

                    index_of_current_item = timing_details.index(i)

                    if index_of_current_item < total_number_of_videos:

                        index_of_current_item = timing_details.index(i)

                        video_list.append("videos/" + str(project_name) +
                                        "/assets/videos/1_final/" + str(index_of_current_item) + ".mp4")

                video_clips = [VideoFileClip(v) for v in video_list]

                finalclip = concatenate_videoclips(video_clips)

                # finalclip = finalclip.set_audio(AudioFileClip(
                #  "videos/" + video_name + "/assets/resources/music/" + key_settings["song"]))

                finalclip.write_videofile("videos/" + project_name + "/" + final_video_name +
                                        ".mp4", fps=60,  audio_bitrate="1000k", bitrate="4000k", codec="libx264")

                video = VideoFileClip("videos/" + project_name +
                                    "/" + final_video_name + ".mp4")


        elif st.session_state.stage == "Project Settings":

            print("Project Settings")
            

        elif st.session_state.stage == "Train Model":

            tab1, tab2 = st.tabs(["Train New Model", "See Existing Models"])

            with tab1:
                images_list = [f for f in os.listdir(f'videos/{project_name}/assets/resources/training_data') if f.endswith('.png')]
        
                images_list.sort(key=lambda f: int(re.sub('\D', '', f)))

                if len(images_list) == 0:
                    st.write("No frames extracted yet")
                
                files_uploaded = ''

                uploaded_files = st.file_uploader("Add training images here", accept_multiple_files=True)
                if uploaded_files is not None:
                    for uploaded_file in uploaded_files:
                        file_details = {"FileName":uploaded_file.name,"FileType":uploaded_file.type}
                        st.write(file_details)
                        img = Image.open(uploaded_file)        
                        with open(os.path.join(f"videos/{project_name}/assets/resources/training_data",uploaded_file.name),"wb") as f: 
                            f.write(uploaded_file.getbuffer())         
                            st.success("Saved File") 
                            # apend the image to the list
                            images_list.append(uploaded_file.name)
                
                                            
                images_for_model = []                    

                for image_name in images_list:
                    index_of_current_item = images_list.index(image_name)
                    st.subheader(f'{index_of_current_item}:')                        
                    image = Image.open(f'videos/{project_name}/assets/resources/training_data/{image_name}') 
                    st.image(image, width=400) 
                    yes = st.checkbox(f'Add {index_of_current_item} to model')    

                    if yes:
                        images_for_model.append(index_of_current_item)
                    else:
                        if index_of_current_item in images_for_model:
                            images_for_model.remove(index_of_current_item)
                
                st.sidebar.subheader("Images for model")

                st.sidebar.write(f"You've selected {len(images_for_model)} image.")

                if len(images_for_model) < 7:
                    st.sidebar.write("Select at least 7 images for model training")
                    st.sidebar.button("Train Model",disabled=True)

                else:
                    st.sidebar.button("Train Model",disabled=False)
            
            with tab2:
                st.write("This is the tab 2")

                  

if __name__ == '__main__':
    main()

