import contextlib
import json
import re

import obspython as obs
import pywinctl as p


@contextlib.contextmanager
def frontend_get_current_scene():
    """
    Called to get the currently active scene.
    Returns:
        A new reference to the currently active scene.
    """
    current_scene = obs.obs_frontend_get_current_scene()
    try:
        yield current_scene
    finally:
        obs.obs_source_release(current_scene)


@contextlib.contextmanager
def scene_enum_items(scene):
    """
    Enumerates scene items within a scene.
    Parameters:
        scene - obs_scene_t object to enumerate items from.
    Returns:
        List of scene items.
    """
    scene_items = obs.obs_scene_enum_items(scene)
    try:
        yield scene_items
    finally:
        obs.sceneitem_list_release(scene_items)


@contextlib.contextmanager
def source_get_settings(source):
    """
    Called to get the settings for a source.
    Returns:
        The settings string for a source.
    """
    settings = obs.obs_source_get_settings(source)
    try:
        yield settings
    finally:
        obs.obs_data_release(settings)


@contextlib.contextmanager
def enum_sources():
    """
    Enumerates all sources.
    Returns:
        An array of reference-incremented sources.
    """
    sources = obs.obs_enum_sources()
    try:
        yield sources
    finally:
        obs.source_list_release(sources)


@contextlib.contextmanager
def data_create_from_json(json_string):
    """
    Creates a data object from a Json string.
    Parameters:
        json_string - Json string
    Returns:
        A new reference to a data object.
    """
    data = obs.obs_data_create_from_json(json_string)
    try:
        yield data
    finally:
        obs.obs_data_release(data)


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
    with enum_sources() as sources:
        if sources is not None:
            for source in sources:
                source_id = obs.obs_source_get_id(source)
                if source_id in ["window_capture", "xcomposite_input"]:
                    name = obs.obs_source_get_name(source)
                    obs.obs_property_list_add_string(p, name, name)
        else:
            print("No sources found. Please add a capture source to a scene first.")
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
        settings - Settings associated with the script.
    """
    global config_source_name, config_executable, config_window_match, config_retry_count
    print("Script settings updated.")
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
    """
    Searches for a window that is owned by the executable and title matches the regular expression specified. It will return the first window that matches and exit.
    Parameters:
        executable - The name of the executable that owns the window.
        re_title - Regular expression to use when matching a window title.
    Returns:
        PyWinCtl Window object that is owned by the executable and has a title that matches the regular expression specified in the re_title parameter.
    """
    global config_retry_count
    exec_lower = executable.lower()
    print("Searching for '%s' owned by '%s'." % (re_title, executable))
    for i in range(config_retry_count+1):
        for window in enum_windows():
            if window.getAppName() == exec_lower and re.match(re_title, window.title) is not None:
                print("\tMatching window found: %s" % window.title)
                print("\tSetting watchdog to see if window closes.")
                # TODO: If a watchdog is already set, dont set another one.
                window.watchdog.start(isAliveCB=on_window_close)
                # TODO: Add a watchdog for window title change - changedTitleCB.
                window.watchdog.setTryToFind(True)
                return window
        print("\tNo match for '%s' owned by '%s'." % (re_title, executable))
        if i < config_retry_count:
            print("\tRetry %s..." % str(i+1))
    print("Retries exceeded, giving up." % (executable, re_title))
    return None


def on_window_close(isAlive):
    # TODO: Test for errors
    global config_source_name, config_executable, config_window_match
    if isAlive == False:
        print("Window has been closed!")
        new_window = match_window(config_executable, config_window_match)
        # new_window = match_window('retroarch', 'RetroArch.*')
        if new_window is not None:
            stale_settings = get_source_settings(config_source_name, ["window_capture", "xcomposite_input"])
            # stale_settings = get_source_settings("RetroArch", ["window_capture", "xcomposite_input"])
            new_settings = stale_settings
            new_settings["window"]="%s:%s" % (new_window.title, new_window.getAppName())
            new_settings["capture_window"] = "%s\r\n%s\r\n%s" % (new_window.getHandle(), new_window.title, new_window.getAppName())
            # if stale_settings != new_settings:
            print("\tUpdating source settings...")
            print("\t\tStale settings:", stale_settings)
            update_source_settings(config_source_name, ["window_capture", "xcomposite_input"], new_settings)
            # update_source_settings("RetroArch",["window_capture", "xcomposite_input"],str(new_settings))
            print("\t\tUpdated settings:",get_source_settings("RetroArch", ["window_capture", "xcomposite_input"]))

# TODO: Define on_window_title_change()
def update_source_settings(source_name, source_types, settings):
    """
    Given a source name and type, this function will return the capture source settings as a JSON object.
    Parameters:
        source_name - The name of the capture source
        source_types - The source types to check
        settings - A settings object
    """
    # TODO: Test for pieces not existing
    with frontend_get_current_scene() as current_scene:
        scene = obs.obs_scene_from_source(current_scene)
        with scene_enum_items(scene) as scene_items:
            for scene_item in scene_items:
                capture_source = obs.obs_sceneitem_get_source(scene_item)
                capture_source_type = obs.obs_source_get_unversioned_id(capture_source)
                capture_source_name = obs.obs_source_get_name(capture_source)
                if capture_source_type in source_types and capture_source_name == source_name:
                    with data_create_from_json(json.dumps(settings)) as data:
                        obs.obs_source_update(capture_source, data)
def get_source_settings(source_name, source_types):
    """
    Given a source name and type, this function will return the capture source settings as a JSON object.
    Parameters:
        source_name - The name of the capture source
        source_types - The source types to check
    Returns:
        A JSON object containing the settings of the matching capture source.
    """
    # TODO: Test for pieces not existing
    source_settings = None
    with frontend_get_current_scene() as current_scene:
        scene = obs.obs_scene_from_source(current_scene)
        with scene_enum_items(scene) as scene_items:
            for scene_item in scene_items:
                capture_source = obs.obs_sceneitem_get_source(scene_item)
                capture_source_type = obs.obs_source_get_unversioned_id(capture_source)
                capture_source_name = obs.obs_source_get_name(capture_source)
                if capture_source_type in source_types and capture_source_name == source_name:
                    with source_get_settings(capture_source) as settings:
                        source_settings = json.loads(obs.obs_data_get_json(settings))
    return source_settings



def script_load(settings):
    """
    Called on script startup with specific settings associated with the script. The settings parameter provided is not typically used for settings that are set by the user; instead the parameter is used for any extra internal settings data that may be used in the script.
    Parameters:
        settings - Settings associated with the script.
    """
    print("Script loaded.")
    # x = get_source_settings("RetroArch", ["window_capture", "xcomposite_input"])
    # match_window(config_executable, config_window_match)
    # TODO: Make a graceful entry point into this script.

