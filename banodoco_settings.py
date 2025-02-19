import copy
import time
import uuid
import streamlit as st

from PIL import Image
from shared.constants import SERVER, AIModelCategory, GuidanceType, InternalFileType, ServerType
from shared.logging.constants import LoggingType
from shared.logging.logging import app_logger
from shared.constants import AnimationStyleType
from ui_components.methods.common_methods import add_image_variant
from ui_components.methods.file_methods import save_or_host_file
from ui_components.models import InternalAppSettingObject, InternalFrameTimingObject, InternalProjectObject, InternalUserObject
from utils.common_utils import create_working_assets
from utils.constants import ML_MODEL_LIST
from utils.data_repo.data_repo import DataRepo


def wait_for_db_ready():
    data_repo = DataRepo()
    while True:
        try:
            user_count = data_repo.get_total_user_count()
            break
        except Exception as e:
            app_logger.log(LoggingType.DEBUG, 'waiting for db...')
            time.sleep(3)

def project_init():
    from utils.data_repo.data_repo import DataRepo
    data_repo = DataRepo()

    wait_for_db_ready()
    user_count = data_repo.get_total_user_count()
    # create a user if not already present (if dev mode)
    # if this is the local server with no user than create one and related data
    if SERVER == ServerType.DEVELOPMENT.value and not user_count:
        user_data = {
            "name" : "banodoco_user",
            "email" : "banodoco@tempuser.com",
            "password" : "123",
            "type" : "user"
        }
        user: InternalUserObject = data_repo.create_user(**user_data)
        app_logger.log(LoggingType.INFO, "new temp user created: " + user.name)

        create_new_user_data(user)
    # creating data for online user
    else:
        app_settings: InternalAppSettingObject = data_repo.get_app_setting_from_uuid()
        if not app_settings:
            online_user = data_repo.get_first_active_user()
            create_new_user_data(online_user)

    # create encryption key if not already present (not applicable in dev mode)
    # env_vars = dotenv_values('.env')
    # desired_key = 'FERNET_KEY'
    # global ENCRYPTION_KEY
    # if desired_key in env_vars:
    #     ENCRYPTION_KEY = env_vars[desired_key].decode()
    # else:
    #     from cryptography.fernet import Fernet

    #     secret_key = Fernet.generate_key()
    #     with open('.env', 'a') as env_file:
    #         env_file.write(f'FERNET_KEY={secret_key.decode()}\n')
        
    #     ENCRYPTION_KEY = secret_key.decode()


# sample data required for starting the project like app settings, project settings
def create_new_user_data(user: InternalUserObject):
    data_repo = DataRepo()
    
    setting_data = {
        "user_id": user.uuid,
        "welcome_state": 0
    }

    app_setting = data_repo.create_app_setting(**setting_data)

    create_new_project(user, 'my_first_project')


def create_new_project(user: InternalUserObject, project_name: str, width=512, height=512):
    data_repo = DataRepo()

    # creating a new project for this user
    project_data = {
        "user_id": user.uuid,
        "name": project_name,
        'width': width,
        'height': height
    }
    project: InternalProjectObject = data_repo.create_project(**project_data)

    # create a default first shot
    shot_data = {
        "project_uuid": project.uuid,
        "desc": "",
        "duration": 10
    }

    shot = data_repo.create_shot(**shot_data)

    # NOTE: removing sample timing frame
    # create a sample timing frame
    # st.session_state["project_uuid"] = project.uuid
    # sample_file_location = "sample_assets/sample_images/v.jpeg"
    # img = Image.open(sample_file_location)
    # img = img.resize((width, height))

    # unique_file_name = f"{str(uuid.uuid4())}.png"
    # file_location = f"videos/{project.uuid}/resources/prompt_images/{unique_file_name}"
    # hosted_url = save_or_host_file(img, file_location, mime_type='image/png', dim=(width, height))
    # file_data = {
    #     "name": str(uuid.uuid4()),
    #     "type": InternalFileType.IMAGE.value,
    #     "project_id": project.uuid,
    #     "dim": (width, height),
    # }

    # if hosted_url:
    #     file_data.update({'hosted_url': hosted_url})
    # else:
    #     file_data.update({'local_path': file_location})

    # source_image = data_repo.create_file(**file_data)

    # timing_data = {
    #     "frame_time": 0.0,
    #     "aux_frame_index": 0,
    #     "source_image_id": source_image.uuid,
    #     "shot_id": shot.uuid,
    # }
    # timing: InternalFrameTimingObject = data_repo.create_timing(**timing_data)

    # add_image_variant(source_image.uuid, timing.uuid)

    # create default ai models
    model_list = create_predefined_models(user)

    # creating a project settings for this
    project_setting_data = {
        "project_id" : project.uuid,
        "input_type" : "video",
        "width" : width,
        "height" : height,
        "default_model_id": model_list[0].uuid
    }

    _ = data_repo.create_project_setting(**project_setting_data)

    create_working_assets(project.uuid)

    return project, shot
    

def create_predefined_models(user):
    data_repo = DataRepo()

    # create predefined models
    data = []
    predefined_model_list = copy.deepcopy(ML_MODEL_LIST)
    for m in predefined_model_list:
        if 'enabled' in m and m['enabled']:
            del m['enabled']
            m['user_id'] = user.uuid
            data.append(m)

    # only creating pre-defined models for the first time
    available_models = data_repo.get_all_ai_model_list(\
        model_category_list=[AIModelCategory.BASE_SD.value], user_id=user.uuid, custom_trained=None)
    
    if available_models and len(available_models):
        return available_models

    model_list = []
    for model in data:
        model_list.append(data_repo.create_ai_model(**model))

    return model_list

    

    