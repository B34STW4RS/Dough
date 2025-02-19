import time
import streamlit as st

from shared.constants import InferenceParamType, InferenceStatus, InternalFileTag, InternalFileType
from ui_components.widgets.frame_movement_widgets import jump_to_single_frame_view_button
import json
import math
from ui_components.widgets.frame_selector import update_current_frame_index

from utils.data_repo.data_repo import DataRepo
from utils.ml_processor.constants import ML_MODEL, MODEL_FILTERS

def sidebar_logger(shot_uuid):
    data_repo = DataRepo()
    shot = data_repo.get_shot_from_uuid(shot_uuid)
    timing_list = data_repo.get_timing_list_from_shot(shot_uuid)
    a1, _, a3 = st.columns([1, 0.2, 1])

    refresh_disabled = False # not any(log.status in [InferenceStatus.QUEUED.value, InferenceStatus.IN_PROGRESS.value] for log in log_list)
    if a1.button("Refresh log", disabled=refresh_disabled, help="You can also press 'r' on your keyboard to refresh."): st.rerun()

    status_option = st.radio("Statuses to display:", options=["All", "In Progress", "Succeeded", "Failed"], key="status_option", index=0, horizontal=True)
    
    status_list = None
    if status_option == "In Progress":
        status_list = [InferenceStatus.QUEUED.value, InferenceStatus.IN_PROGRESS.value]
    elif status_option == "Succeeded":
        status_list = [InferenceStatus.COMPLETED.value]
    elif status_option == "Failed":
        status_list = [InferenceStatus.FAILED.value]

    b1, b2 = st.columns([1, 1])

    project_setting = data_repo.get_project_setting(shot.project.uuid)
    
    page_number = b1.number_input('Page number', min_value=1, max_value=project_setting.total_log_pages, value=1, step=1)
    items_per_page = b2.slider("Items per page", min_value=1, max_value=20, value=5, step=1)
    
    selected_option = st.selectbox(
        "Choose an option",
        ["All"] + [m.display_name() for m in MODEL_FILTERS]
    )
    
    log_filter_data = {
        "project_id" : shot.project.uuid,
        "page" : page_number,
        "data_per_page" : items_per_page,
        "status_list" : status_list
    }
    
    if selected_option != "All":
        log_filter_data["model_name_list"] = [selected_option]      # multiple models can be entered here for filtering if needed
    
    log_list, total_page_count = data_repo.get_all_inference_log_list(
        **log_filter_data
    )
    
    if project_setting.total_log_pages != total_page_count:
        project_setting.total_log_pages = total_page_count
        st.rerun()
    
    st.write("Total page count: ", total_page_count)
    # display_list = log_list[(page_number - 1) * items_per_page : page_number * items_per_page]                

    if log_list and len(log_list):
        file_list = data_repo.get_file_list_from_log_uuid_list([log.uuid for log in log_list])
        log_file_dict = {}
        for file in file_list:
            log_file_dict[str(file.inference_log.uuid)] = file

        st.markdown("---")

        for _, log in enumerate(log_list):
            origin_data = json.loads(log.input_params).get(InferenceParamType.ORIGIN_DATA.value, None)
            if not log.status:
                continue
            
            output_url = None
            if log.uuid in log_file_dict:
                output_url = log_file_dict[log.uuid].location

            c1, c2, c3 = st.columns([1, 1 if output_url else 0.01, 1])

            with c1:                
                input_params = json.loads(log.input_params)
                st.caption(f"Prompt:")
                prompt = input_params.get('prompt', 'No prompt found')                
                st.write(f'"{prompt[:30]}..."' if len(prompt) > 30 else f'"{prompt}"')
                st.caption(f"Model:")
                try:
                    st.write(json.loads(log.output_details)['model_name'].split('/')[-1])
                except Exception as e:
                    st.write('')
                            
            with c2:
                if output_url:                                              
                    if output_url.endswith('png') or output_url.endswith('jpg') or output_url.endswith('jpeg') or output_url.endswith('gif'):
                        st.image(output_url)
                    elif output_url.endswith('mp4'):
                        st.video(output_url, format='mp4', start_time=0)
                    else:
                        st.info("No data to display")         
        
            with c3:
                if log.status == InferenceStatus.COMPLETED.value:
                    st.success("Completed")
                elif log.status == InferenceStatus.FAILED.value:
                    st.warning("Failed")
                elif log.status == InferenceStatus.QUEUED.value:
                    st.info("Queued")
                elif log.status == InferenceStatus.IN_PROGRESS.value:
                    st.info("In progress")
                elif log.status == InferenceStatus.CANCELED.value:
                    st.warning("Canceled")
                
                log_file = log_file_dict[log.uuid] if log.uuid in log_file_dict else None
                if log_file:
                    if log_file.type == InternalFileType.IMAGE.value and log_file.tag != InternalFileTag.SHORTLISTED_GALLERY_IMAGE.value:
                        if st.button("Add to shortlist ➕", key=f"sidebar_shortlist_{log_file.uuid}",use_container_width=True, help="Add to shortlist"):
                            data_repo.update_file(log_file.uuid, tag=InternalFileTag.SHORTLISTED_GALLERY_IMAGE.value)
                            st.success("Added To Shortlist")
                            time.sleep(0.3)
                            st.rerun()


                if output_url and origin_data and 'timing_uuid' in origin_data and origin_data['timing_uuid']:
                    timing = data_repo.get_timing_from_uuid(origin_data['timing_uuid'])
                    if timing and st.session_state['frame_styling_view_type'] != "Timeline":
                        jump_to_single_frame_view_button(timing.aux_frame_index + 1, timing_list, 'sidebar_'+str(log.uuid))     

                    else:
                        if st.session_state['page'] != "Explore":
                            if st.button(f"Jump to explorer", key=str(log.uuid)):
                                # TODO: fix this
                                st.session_state['main_view_type'] = "Creative Process"
                                st.session_state['frame_styling_view_type_index'] = 0
                                st.session_state['frame_styling_view_type'] = "Explorer"
                                
                                st.rerun()
                

            st.markdown("---")