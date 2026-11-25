"""
HATI : Undercity - PCG Biome Core test map.

Builds /Game/HATI/Maps/Dev/L_Dev_PCGBiome: a 40 x 40 m blockout room (mesh floor, not a
landscape) with a contaminated zone, a main path and cover, plus the PCG Biome Core actors:
  BP_PCGBiomeCore             the generator that spawns everything
  BP_PCGBiomeVolume           "contamination clutter" zone over the red hazard floor
  BP_PCGBiomeExclusionVolume  keeps the main path (and its cover) clear
The biome uses the Biome Sample "Landslide" definition (boulders) as stand-in rubble until we
have our own scrap assets.

Known (2026-11-25): spawns 0 instances here. The sample/template generator graphs sample with
Get Landscape Data, and this room has a mesh floor, no landscape. See README "PCG Biome Core 테스트".

Needs the PCG, PCGBiomeCore and PCGBiomeSample plugins (enabled in the .uproject) and the
MI_BO_* materials from setup_blockout.py. Needs the full editor:
  UnrealEditor.exe HATI_Undercity.uproject -ExecutePythonScript="Tools/setup_pcg_biome_test.py" -HATIQuit
Re-runnable: it clears and rebuilds the map.
"""
import unreal

EAL = unreal.EditorAssetLibrary
LES = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)

MAP = "/Game/HATI/Maps/Dev/L_Dev_PCGBiome"
MAT = "/Game/HATI/Blockout/Materials/MI_BO_"
CUBE = "/Game/_Template/LevelPrototyping/Meshes/SM_Cube"
BIOME_BP = "/PCGBiomeCore/Blueprints/"
BIOME_DEF = "/PCGBiomeSample/BiomeDefinitions/Landslide"
BIOME_ASSET = "/PCGBiomeSample/BiomeAssets/Landslide"
GEN_WAIT_SEC = 90.0


def log(msg):
    unreal.log("[HATI-PCG] " + msg)


def warn(msg):
    unreal.log_warning("[HATI-PCG] " + msg)


# ---------------------------------------------------------------- map / blockout helpers
def new_map(path):
    if EAL.does_asset_exist(path):
        if not LES.load_level(path):
            raise RuntimeError("could not open " + path)
        EAS.destroy_actors([a for a in EAS.get_all_level_actors() if not isinstance(a, unreal.WorldSettings)])
        return
    try:
        ok = LES.new_level(path, False)
    except TypeError:
        ok = LES.new_level(path)
    if not ok:
        raise RuntimeError("could not create " + path)


class Builder:
    def __init__(self):
        self.mesh = unreal.load_asset(CUBE)
        bb = self.mesh.get_bounding_box()
        self.mmin = bb.min
        self.msize = bb.max - bb.min
        self.mats = {}

    def mat(self, name):
        if name not in self.mats:
            self.mats[name] = unreal.load_asset(MAT + name)
        return self.mats[name]

    def block(self, label, minc, size, mat, folder="Blockout"):
        """Axis-aligned SM_Cube whose bounds start at `minc` and span `size` (cm)."""
        scale = unreal.Vector(size[0] / self.msize.x, size[1] / self.msize.y, size[2] / self.msize.z)
        loc = unreal.Vector(minc[0] - self.mmin.x * scale.x, minc[1] - self.mmin.y * scale.y, minc[2] - self.mmin.z * scale.z)
        a = EAS.spawn_actor_from_object(self.mesh, loc, unreal.Rotator())
        a.set_actor_scale3d(scale)
        a.static_mesh_component.set_material(0, self.mat(mat))
        a.set_actor_label(label)
        a.set_folder_path(folder)
        return a

    def text(self, txt, loc, size=40, yaw=180, color=(255, 255, 255)):
        a = EAS.spawn_actor_from_class(unreal.TextRenderActor, unreal.Vector(*loc), unreal.Rotator(0, 0, yaw))
        c = a.text_render
        c.set_text(txt)
        c.set_editor_property("world_size", size)
        c.set_editor_property("horizontal_alignment", unreal.HorizTextAligment.EHTA_CENTER)
        c.set_editor_property("text_render_color", unreal.Color(r=color[0], g=color[1], b=color[2], a=255))
        a.set_actor_label("TXT_" + txt.split("\n")[0][:24])
        a.set_folder_path("Labels")
        return a


def add_lighting_and_start(start, yaw):
    def spawn(cls, loc=(0, 0, 0), rot=(0, 0, 0)):
        a = EAS.spawn_actor_from_class(cls, unreal.Vector(*loc), unreal.Rotator(roll=rot[2], pitch=rot[0], yaw=rot[1]))
        a.set_folder_path("Lighting")
        return a

    sun = spawn(unreal.DirectionalLight, (0, 0, 2000), (-50, 35, 0))
    sun.light_component.set_editor_property("atmosphere_sun_light", True)
    sun.light_component.set_editor_property("intensity", 8.0)
    sun.light_component.set_mobility(unreal.ComponentMobility.MOVABLE)
    sky = spawn(unreal.SkyLight, (0, 0, 1500))
    sky.light_component.set_mobility(unreal.ComponentMobility.MOVABLE)
    sky.light_component.set_editor_property("real_time_capture", True)
    spawn(unreal.SkyAtmosphere)
    fog = spawn(unreal.ExponentialHeightFog, (0, 0, -100))
    fog.component.set_editor_property("fog_density", 0.01)
    ps = EAS.spawn_actor_from_class(unreal.PlayerStart, unreal.Vector(*start), unreal.Rotator(0, 0, yaw))
    ps.set_folder_path("Gameplay")


# ---------------------------------------------------------------- biome helpers
def spawn_bp(name, loc, scale=(1, 1, 1), label=None):
    cls = unreal.EditorAssetLibrary.load_blueprint_class(BIOME_BP + name)
    if cls is None:
        raise RuntimeError("missing blueprint %s%s - is the PCGBiomeCore plugin enabled?" % (BIOME_BP, name))
    a = EAS.spawn_actor_from_class(cls, unreal.Vector(*loc), unreal.Rotator())
    a.set_actor_scale3d(unreal.Vector(*scale))
    a.set_actor_label(label or name)
    a.set_folder_path("PCG")
    return a


def try_set(actor, names, value):
    """Blueprint variable names are not documented; try the likely spellings and log which one stuck."""
    for n in names:
        try:
            actor.set_editor_property(n, value)
            log("%s.%s set" % (actor.get_actor_label(), n))
            return True
        except Exception:
            pass
    warn("%s: none of %s exists - set it by hand in the Details panel" % (actor.get_actor_label(), names))
    return False


def pcg_components(actor):
    return actor.get_components_by_class(unreal.PCGComponent)


def generate(actor):
    for c in pcg_components(actor):
        for fn in ("generate_local", "generate"):
            if hasattr(c, fn):
                try:
                    getattr(c, fn)(True)
                    log("%s: %s(force) on %s" % (actor.get_actor_label(), fn, c.get_name()))
                    break
                except Exception as e:
                    warn("%s.%s failed: %s" % (c.get_name(), fn, e))


def count_spawned():
    """Instances in PCG-made ISM/HISM components, across all actors (incl. PCG partition actors)."""
    total = 0
    for a in EAS.get_all_level_actors():
        for c in a.get_components_by_class(unreal.InstancedStaticMeshComponent):
            total += c.get_instance_count()
    return total


# ---------------------------------------------------------------- build
def build():
    new_map(MAP)
    b = Builder()
    # room: 40 x 40 m, floor top at z=0, walls 6 m
    b.block("Floor", (-2000, -2000, -20), (4000, 4000, 20), "Floor")
    for lbl, minc, size in [
        ("Wall_N", (-2000, 2000, 0), (4000, 100, 600)),
        ("Wall_S", (-2000, -2100, 0), (4000, 100, 600)),
        ("Wall_E", (2000, -2100, 0), (100, 4200, 600)),
        ("Wall_W", (-2100, -2100, 0), (100, 4200, 600)),
    ]:
        b.block(lbl, minc, size, "Wall")
    # main path along +X through the middle (kept clear by the exclusion volume)
    b.block("Path_Main", (-2000, -200, 0), (4000, 400, 2), "Path")
    for i, x in enumerate((-1200, -200, 800)):
        b.block("Cover_%d" % i, (x, 250, 0), (300, 80, 100), "Cover")
    # contaminated zone (north-east quarter) - biome target
    b.block("Hazard_Floor", (0, 400, 0), (1900, 1500, 2), "Hazard")
    b.block("Toxic_Pool", (900, 1100, 0), (500, 400, 4), "Toxic")
    # big props the clutter should wrap around
    b.block("Prop_Container_A", (300, 1500, 0), (600, 240, 260), "Prop")
    b.block("Prop_Tank_B", (1500, 600, 0), (250, 250, 400), "Prop")
    # control area (south-west) - plain floor, no biome, for comparison
    b.block("Interact_Marker", (-1500, -1500, 0), (100, 100, 150), "Interact")

    b.text("PCG BIOME TEST\nzone = Hazard (NE)  /  path = exclusion", (1980, 0, 450), 50)
    b.text("BIOME VOLUME", (950, 1150, 300), 40, color=(255, 120, 120))
    b.text("EXCLUSION (PATH)", (0, 0, 220), 30, color=(200, 200, 200))
    b.text("CONTROL (no biome)", (-1450, -1450, 260), 30, color=(120, 255, 255))

    add_lighting_and_start((-1800, 0, 120), 0)

    # --- PCG Biome Core
    core = spawn_bp("BP_PCGBiomeCore", (0, 0, 0), label="PCG_BiomeCore")
    # BP volumes are unit boxes scaled by the actor (default box extent 100 -> 2 m per scale unit)
    zone = spawn_bp("BP_PCGBiomeVolume", (950, 1150, 200), (9.5, 7.5, 3.0), "PCG_Biome_Contamination")
    excl = spawn_bp("BP_PCGBiomeExclusionVolume", (0, 0, 200), (20.0, 2.5, 3.0), "PCG_Exclusion_Path")
    biome_def = unreal.load_asset(BIOME_DEF)
    if biome_def is None:
        warn("biome definition %s not found - set BiomeDefinition by hand" % BIOME_DEF)
    else:
        try_set(zone, ["Definition", "BiomeDefinition"], biome_def)
    # the definition is only an id; the spawn list lives in BiomeAssets
    biome_asset = unreal.load_asset(BIOME_ASSET)
    if biome_asset is None:
        warn("biome asset %s not found" % BIOME_ASSET)
    else:
        try_set(zone, ["BiomeAssets", "Assets"], [biome_asset])
    return core, zone, excl


def finish(core, zone, excl):
    LES.save_current_level()
    log("saved " + MAP)
    log("PCG components: core=%d zone=%d excl=%d" % tuple(len(pcg_components(a)) for a in (core, zone, excl)))
    for a in (zone, excl, core):
        generate(a)
    state = {"t": 0.0, "last": -1, "stable": 0}

    def tick(dt):
        state["t"] += dt
        n = count_spawned()
        state["stable"] = state["stable"] + 1 if n == state["last"] else 0
        state["last"] = n
        done = state["t"] > GEN_WAIT_SEC or (n > 0 and state["stable"] > 120)
        if not done:
            return
        unreal.unregister_slate_post_tick_callback(handle)
        log("generation result: %d instances after %.0fs" % (n, state["t"]))
        if n == 0:
            warn("nothing spawned - check the biome volume's BiomeDefinition and the surface input (mesh floor, no landscape)")
        LES.save_current_level()
        log("DONE")
        keep_alive(False)
        if "-HATIQuit" in unreal.SystemLibrary.get_command_line():
            unreal.SystemLibrary.quit_editor()

    handle = unreal.register_slate_post_tick_callback(tick)


def keep_alive(on):
    # -ExecutePythonScript quits the editor as soon as the script returns unless told otherwise;
    # we need a few ticks for async PCG generation.
    try:
        unreal.EditorPythonScripting.set_keep_python_script_alive(on)
    except Exception as e:
        warn("keep-alive unavailable: %s" % e)


def main():
    keep_alive(True)
    core, zone, excl = build()
    finish(core, zone, excl)


main()
