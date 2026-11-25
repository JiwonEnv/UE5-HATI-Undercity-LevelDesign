"""
HATI : Undercity - per-map exposure (Post Process Volume) setup.

Rule (README "조명·노출 규칙"):
  - project-wide: Config/DefaultEngine.ini widens the safe exposure range
    (r.EyeAdaptation.CachedLightingPreExposure=6 -> EV -6..14)
  - per map: one unbound Post Process Volume "PPV_Global" sets that map's exposure range (mood)

This script adds or updates PPV_Global in every map listed in PRESETS and saves.
  UnrealEditor.exe HATI_Undercity.uproject -ExecutePythonScript="Tools/setup_post_process.py"
Can also be run from an open editor: Tools > Execute Python Script...
"""
import unreal

LES = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)

PPV_LABEL = "PPV_Global"

# map -> (min EV100, max EV100, exposure compensation)
#   sunny exterior: EV ~10-14 / dark underground: EV ~-2-6 (add scene maps here when lighting starts)
PRESETS = {
    "/Game/HATI/Maps/Dev/L_Dev_PCGBiome_Outdoor": (10.0, 14.0, 0.0),
}


def log(m):
    unreal.log("[HATI-PPV] " + m)


def apply_preset(min_ev, max_ev, bias):
    ppv = None
    for a in EAS.get_all_level_actors():
        if isinstance(a, unreal.PostProcessVolume) and a.get_actor_label() == PPV_LABEL:
            ppv = a
            break
    if ppv is None:
        ppv = EAS.spawn_actor_from_class(unreal.PostProcessVolume, unreal.Vector(0, 0, 0), unreal.Rotator())
        ppv.set_actor_label(PPV_LABEL)
        ppv.set_folder_path("Lighting")
    ppv.set_editor_property("unbound", True)       # Infinite Extent: applies to the whole map
    s = ppv.get_editor_property("settings")
    s.set_editor_property("override_auto_exposure_min_brightness", True)
    s.set_editor_property("auto_exposure_min_brightness", min_ev)
    s.set_editor_property("override_auto_exposure_max_brightness", True)
    s.set_editor_property("auto_exposure_max_brightness", max_ev)
    s.set_editor_property("override_auto_exposure_bias", True)
    s.set_editor_property("auto_exposure_bias", bias)
    ppv.set_editor_property("settings", s)
    return ppv


def main():
    for m, (lo, hi, bias) in PRESETS.items():
        if not LES.load_level(m):
            unreal.log_warning("[HATI-PPV] could not open " + m)
            continue
        apply_preset(lo, hi, bias)
        LES.save_current_level()
        log("%s: PPV_Global EV100 %.1f..%.1f bias %.1f" % (m, lo, hi, bias))
    cv = unreal.SystemLibrary.get_console_variable_float_value("r.EyeAdaptation.CachedLightingPreExposure")
    log("r.EyeAdaptation.CachedLightingPreExposure = %.1f (safe EV %.0f..%.0f)" % (cv, cv - 12, cv + 8))
    log("DONE")


main()
