import re

import obspython as obs
import pywinctl as p


def script_description():
    """
    Called to retrieve a description string to be displayed to the user in the Scripts window.
    """
    return "Window capture for dynamic window titles"


def script_properties():
    """
    Called to define user properties associated with the script. These properties are used to define how to show settings properties to a user.
    Returns:
    obs_properties_t object created via obs_properties_create().
    """
    props = obs.obs_properties_create()
    p = obs.obs_properties_add_list(props, "source", "Window Capture Source", obs.OBS_COMBO_TYPE_LIST,
                                    obs.OBS_COMBO_FORMAT_STRING)
    # Populate the dropdown with appropriate sources
    sources = obs.obs_enum_sources()
    if sources is not None:
        for source in sources:
            source_id = obs.obs_source_get_id(source)
            if source_id in ["window_capture", "xcomposite_input"]:
                name = obs.obs_source_get_name(source)
                obs.obs_property_list_add_string(p, name, name)

        obs.source_list_release(sources)

    obs.obs_properties_add_text(props, "executable", "Executable to Match (e.g. whatsapp.exe)", obs.OBS_TEXT_DEFAULT)
    obs.obs_properties_add_text(props, "window_match", "Regex for Title to Match (e.g. .*video call",
                                obs.OBS_TEXT_DEFAULT)
    obs.obs_properties_add_int(props, "retry_count",
                               "Number of times to retry searching for a window before giving up", min=0, max=50,
                               step=1)
    return props


def script_update(settings):
    """
    Called when the script’s settings (if any) have been changed by the user.
    Parameters:
    settings – Settings associated with the script.
    """
    global config_source_name, config_executable, config_window_match, config_retry_count
    print("Settings updated")
    config_source_name = obs.obs_data_get_string(settings, "source")
    config_executable = obs.obs_data_get_string(settings, "executable")
    config_window_match = obs.obs_data_get_string(settings, "window_match")
    config_retry_count = int(obs.obs_data_get_int(settings, "retry_count"))


def enum_windows():
    windows = []
    for window in p.getAllWindows():
        windows.append(window)
    return windows


def match_window(executable, re_title):
    global config_retry_count
    exec_lower = executable.lower()
    for i in range(config_retry_count+1):
        print("Searching for matching executable %s and window title: %s" % (executable, re_title))
        for window in enum_windows():
            if window.getAppName() == exec_lower and re.match(re_title, window.title) is not None:
                print("Matching Window Found: %s" % window.title)
                print("Setting watchdog to see if window closes.")
                window.watchdog.start(isAliveCB=on_window_close)
                window.watchdog.setTryToFind(True)
                return window
        print("No window matches executable %s and window title: %s" % (executable, re_title))
        if i < config_retry_count:
            print("Retry %s..." % str(i+1))
    return None


def on_window_close(isAlive):
    if isAlive == False:
        print('Window has been closed!')
        global config_source_name, config_executable, config_window_match

        current_scene = obs.obs_frontend_get_current_scene()

        scene = obs.obs_scene_from_source(current_scene)
        scene_items = obs.obs_scene_enum_items(scene)
        for scene_item in scene_items:
            cur_source = obs.obs_sceneitem_get_source(scene_item)
            if (obs.obs_source_get_unversioned_id(cur_source) in ["window_capture", "xcomposite_input"] and
                    obs.obs_source_get_name(cur_source) == config_source_name):
                print("Source matched: %s" % (obs.obs_source_get_name(cur_source)))
                cur_settings = obs.obs_source_get_settings(cur_source)
                print("Current settings: %s" % obs.obs_data_get_json(cur_settings))
                new_window = match_window(config_executable, config_window_match)
                if new_window is not None:
                    # First, update the Window title information
                    old_window_text = obs.obs_data_get_string(cur_settings, "window")
                    new_window_text = "%s:%s" % (new_window.title, new_window.getAppName())
                    print("Old Window Text: %s\r\nNew Window Text: %s" % (old_window_text, new_window_text))
                    if old_window_text != new_window_text:
                        print("Update source window to %s" % new_window_text)
                        obs.obs_data_set_string(cur_settings, "window", new_window_text)
                        obs.obs_source_update(cur_source, cur_settings)
                    # Next, update the Capture Window information
                    old_capture_window = obs.obs_data_get_string(cur_settings, "capture_window")
                    new_capture_window = "%s\r\n%s\r\n%s" % (
                        new_window.getHandle(), new_window.title, new_window.getAppName())
                    print("Old Window Cap: %s\r\nNew Window Cap: %s" % (old_window_text, new_window_text))
                    if old_capture_window != new_capture_window:
                        print("Update source capture to %s" % new_capture_window)
                        obs.obs_data_set_string(cur_settings, "capture_window", new_capture_window)
                        obs.obs_source_update(cur_source, cur_settings)
                    if old_window_text != new_window_text or old_capture_window != new_capture_window:
                        print("Updated settings: %s" % obs.obs_data_get_json(cur_settings))
                obs.obs_data_release(cur_settings)

        obs.sceneitem_list_release(scene_items)


def script_load(settings):
    """
    Called on script startup with specific settings associated with the script. The settings parameter provided is not typically used for settings that are set by the user; instead the parameter is used for any extra internal settings data that may be used in the script.
    Parameters:
    settings – Settings associated with the script.
    """
    print("Script loaded.")
    match_window(config_executable, config_window_match)
    # obs.obs_frontend_add_event_callback(on_event)
