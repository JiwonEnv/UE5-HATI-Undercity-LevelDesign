"""
HATI : Undercity - PCG Biome Core OUTDOOR test (outside the shelter).

Python cannot create a landscape, so this borrows the terrain of Epic's Biome Sample level:
  1. open /PCGBiomeSample/Maps/BiomeSampleLevel (1 km x 1 km landscape, World Partition)
  2. delete Epic's biome placement (texture/volume/spline actors), keep landscape + lighting + BiomeCore
  3. Save As /Game/HATI/Maps/Dev/L_Dev_PCGBiome_Outdoor
  4. lay out our own zones on the flat south-west part of the terrain:
       Wasteland  (Desert biome)            - big sandy zone
       RubbleField (Landslide biome)        - rocks
       DeadForest (ConiferousForest biome)  - overlaps RubbleField to show blending
       road to the shelter gate             - exclusion spline (kept clear)
       shelter gate                         - exclusion volume + purple blockout wall
  5. generate, wait, take a screenshot to Saved/Screenshots, save

Run:
  UnrealEditor.exe HATI_Undercity.uproject -ExecutePythonScript="Tools/setup_pcg_biome_outdoor.py" -HATIQuit
Re-runnable (it re-copies the sample level every time).
"""
import unreal

EAL = unreal.EditorAssetLibrary
LES = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
UES = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)

SRC_MAP = "/PCGBiomeSample/Maps/BiomeSampleLevel"
MAP = "/Game/HATI/Maps/Dev/L_Dev_PCGBiome_Outdoor"
BP = "/PCGBiomeCore/Blueprints/"
SAMPLE = "/PCGBiomeSample/"
GEN_WAIT_SEC = 240.0
SHOT_NAME = "PCGBiome_Outdoor"

# biome actor classes from the sample that we remove (we place our own)
REMOVE_CLASSES = ("BiomeTexture", "BP_PCGBiomeVolume", "BP_PCGBiomeSpline", "CropField", "BiomeCore_Runtime")


def log(m):
    unreal.log("[HATI-PCGO] " + m)


def warn(m):
    unreal.log_warning("[HATI-PCGO] " + m)


def keep_alive(on):
    try:
        unreal.EditorPythonScripting.set_keep_python_script_alive(on)
    except Exception as e:
        warn("keep-alive unavailable: %s" % e)


def world():
    return UES.get_editor_world()


def ground_z(x, y, default=1000.0):
    """Landscape height under (x, y) by a downward line trace."""
    try:
        hit = unreal.SystemLibrary.line_trace_single(
            world(), unreal.Vector(x, y, 50000), unreal.Vector(x, y, -50000),
            unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, True, [], unreal.DrawDebugTrace.NONE, True)
        if hit:
            t = hit.to_tuple()
            # (blocking_hit, initial_overlap, time, distance, location, impact_point, ...)
            if t[0]:
                return t[4].z
    except Exception as e:
        warn("trace failed: %s" % e)
    return default


def try_set(actor, names, value):
    for n in names:
        try:
            actor.set_editor_property(n, value)
            log("%s.%s set" % (actor.get_actor_label(), n))
            return True
        except Exception:
            pass
    warn("%s: none of %s exists" % (actor.get_actor_label(), names))
    return False


def try_get(actor, names):
    for n in names:
        try:
            return n, actor.get_editor_property(n)
        except Exception:
            pass
    return None, None


# ---------------------------------------------------------------- 1-3: copy terrain
def copy_sample_level():
    if not LES.load_level(SRC_MAP):
        raise RuntimeError("could not open " + SRC_MAP + " (PCGBiomeSample plugin enabled?)")
    actors = EAS.get_all_level_actors()
    # record how Epic configured its volumes (for reference in the log)
    for a in actors:
        cn = a.get_class().get_name()
        if "BiomeVolume" in cn or "BiomeTexture" in cn or "BiomeSpline" in cn:
            _, d = try_get(a, ["Definition"])
            _, s = try_get(a, ["Assets"])
            log("sample %s (%s): Definition=%s Assets=%s scale=%s" % (
                a.get_actor_label(), cn, d.get_name() if d else None,
                [x.get_name() for x in s] if s else None, a.get_actor_scale3d()))
    doomed = [a for a in actors if any(k in a.get_class().get_name() for k in REMOVE_CLASSES)]
    log("removing %d sample biome actors" % len(doomed))
    EAS.destroy_actors(doomed)
    if EAL.does_asset_exist(MAP):
        EAL.delete_asset(MAP)
    ok = unreal.EditorLoadingAndSavingUtils.save_map(world(), MAP)
    if not ok:
        raise RuntimeError("save as failed: " + MAP)
    log("saved copy as " + MAP)
    if not LES.load_level(MAP):
        raise RuntimeError("could not reopen " + MAP)


# ---------------------------------------------------------------- 4: our layout
def spawn_bp(name, loc, label):
    cls = EAL.load_blueprint_class(BP + name)
    a = EAS.spawn_actor_from_class(cls, unreal.Vector(*loc), unreal.Rotator())
    a.set_actor_label(label)
    a.set_folder_path("PCG_HATI")
    return a


def fit_box(actor, size_xyz):
    """Scale a BP volume so its world bounds become size_xyz (cm)."""
    actor.set_actor_scale3d(unreal.Vector(1, 1, 1))
    ext = actor.get_actor_bounds(False)[1]
    if ext.x <= 0:
        warn("%s has zero bounds" % actor.get_actor_label())
        return
    actor.set_actor_scale3d(unreal.Vector(size_xyz[0] / (2 * ext.x), size_xyz[1] / (2 * ext.y), size_xyz[2] / (2 * ext.z)))


def biome_volume(label, biome, center_xy, size_xy):
    z = ground_z(*center_xy)
    v = spawn_bp("BP_PCGBiomeVolume", (center_xy[0], center_xy[1], z), label)
    fit_box(v, (size_xy[0], size_xy[1], 8000))
    d = unreal.load_asset(SAMPLE + "BiomeDefinitions/" + biome)
    s = unreal.load_asset(SAMPLE + "BiomeAssets/" + biome)
    if d:
        try_set(v, ["Definition"], d)
    if s:
        try_set(v, ["Assets"], [s])
    label_text(label + "\n(" + biome + ")", (center_xy[0], center_xy[1], z + 1500))
    return v


def label_text(txt, loc, size=600, color=(255, 255, 255)):
    a = EAS.spawn_actor_from_class(unreal.TextRenderActor, unreal.Vector(*loc), unreal.Rotator(0, 0, 180))
    c = a.text_render
    c.set_text(txt)
    c.set_editor_property("world_size", size)
    c.set_editor_property("horizontal_alignment", unreal.HorizTextAligment.EHTA_CENTER)
    c.set_editor_property("text_render_color", unreal.Color(r=color[0], g=color[1], b=color[2], a=255))
    a.set_actor_label("TXT_" + txt.split("\n")[0][:24])
    a.set_folder_path("Labels")


def blockout_wall(label, minc, size):
    mesh = unreal.load_asset("/Game/LevelPrototyping/Meshes/SM_Cube")
    bb = mesh.get_bounding_box()
    ms = bb.max - bb.min
    scale = unreal.Vector(size[0] / ms.x, size[1] / ms.y, size[2] / ms.z)
    loc = unreal.Vector(minc[0] - bb.min.x * scale.x, minc[1] - bb.min.y * scale.y, minc[2] - bb.min.z * scale.z)
    a = EAS.spawn_actor_from_object(mesh, loc, unreal.Rotator())
    a.set_actor_scale3d(scale)
    m = unreal.load_asset("/Game/HATI/Blockout/Materials/MI_BO_Restricted")
    if m:
        a.static_mesh_component.set_material(0, m)
    a.set_actor_label(label)
    a.set_folder_path("Blockout")
    return a


def build_layout():
    # flat south-west part of the sample terrain: x -25000..0, y -25000..25000
    biome_volume("Wasteland", "Desert", (-14000, -11000), (20000, 18000))
    biome_volume("RubbleField", "Landslide", (-12000, 9000), (14000, 14000))
    biome_volume("DeadForest", "ConiferousForest", (-21000, 13000), (10000, 16000))

    # shelter gate: a purple wall the clutter must keep away from
    gz = ground_z(-3000, 0)
    blockout_wall("Shelter_OuterWall", (-3000, -4000, gz - 500), (1500, 8000, 4000))
    label_text("SHELTER GATE", (-3500, 0, gz + 4200), 700, (200, 140, 255))
    ex = spawn_bp("BP_PCGBiomeExclusionVolume", (-6000, 0, gz), "Exclusion_Gate")
    fit_box(ex, (7000, 9000, 8000))

    # road from the wasteland to the gate - exclusion spline
    road = spawn_bp("BP_PCGBiomeExclusionSpline", (0, 0, 0), "Exclusion_Road")
    pts = [(-23000, -18000), (-17000, -9000), (-11000, -3000), (-6000, 0)]
    sp = road.get_component_by_class(unreal.SplineComponent)
    if sp:
        sp.set_spline_points([unreal.Vector(x, y, ground_z(x, y)) for x, y in pts], unreal.SplineCoordinateSpace.WORLD, True)
        log("road spline: %d points" % sp.get_number_of_spline_points())
    else:
        warn("exclusion spline has no SplineComponent")
    label_text("ROAD (exclusion spline)", (-17000, -9000, ground_z(-17000, -9000) + 1200), 500, (220, 220, 220))

    # player start near the gate
    ps = EAS.spawn_actor_from_class(unreal.PlayerStart, unreal.Vector(-8000, 0, gz + 200), unreal.Rotator(0, 0, 180))
    ps.set_folder_path("Gameplay")


# ---------------------------------------------------------------- 5: generate / screenshot
def biome_cores():
    return [a for a in EAS.get_all_level_actors() if a.get_class().get_name() == "BP_PCGBiomeCore_C"]


def generate_all():
    for a in EAS.get_all_level_actors():
        if "PCGBiome" not in a.get_class().get_name():
            continue
        for c in a.get_components_by_class(unreal.PCGComponent):
            try:
                c.generate_local(True)
                log("generate %s / %s" % (a.get_actor_label(), c.get_name()))
            except Exception as e:
                warn("generate failed on %s: %s" % (a.get_actor_label(), e))


def count_spawned():
    n = 0
    for a in EAS.get_all_level_actors():
        for c in a.get_components_by_class(unreal.InstancedStaticMeshComponent):
            n += c.get_instance_count()
    return n


def main():
    keep_alive(True)
    copy_sample_level()
    build_layout()
    LES.save_current_level()
    log("BiomeCore actors: %d" % len(biome_cores()))
    generate_all()

    st = {"t": 0.0, "last": -1, "stable": 0, "phase": "gen", "shot_t": 0.0}

    def tick(dt):
        st["t"] += dt
        if st["phase"] == "gen":
            n = count_spawned()
            st["stable"] = st["stable"] + 1 if n == st["last"] else 0
            st["last"] = n
            if st["t"] > GEN_WAIT_SEC or (n > 0 and st["stable"] > 300):
                log("generation result: %d instances after %.0fs" % (n, st["t"]))
                UES.set_level_viewport_camera_info(unreal.Vector(-40000, -2000, 16000), unreal.Rotator(0, -28, 0))
                st["phase"], st["shot_t"] = "cam", st["t"]
        elif st["phase"] == "cam" and st["t"] - st["shot_t"] > 8:
            unreal.SystemLibrary.execute_console_command(world(), "HighResShot 1920x1080 filename=" + SHOT_NAME)
            st["phase"], st["shot_t"] = "shot", st["t"]
        elif st["phase"] == "shot" and st["t"] - st["shot_t"] > 8:
            unreal.unregister_slate_post_tick_callback(handle)
            LES.save_current_level()
            log("DONE")
            keep_alive(False)
            if "-HATIQuit" in unreal.SystemLibrary.get_command_line():
                unreal.SystemLibrary.quit_editor()

    handle = unreal.register_slate_post_tick_callback(tick)


main()
