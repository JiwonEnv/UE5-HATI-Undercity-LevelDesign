"""
HATI : Undercity - blockout foundation setup.

Run (re-runnable; it rebuilds the assets it owns). Needs the full editor, not the
-run=pythonscript commandlet, because actors cannot be spawned in commandlet mode:
  UnrealEditor.exe HATI_Undercity.uproject -ExecutePythonScript="Tools/setup_blockout.py" -HATIQuit
Or from an open editor: Tools > Execute Python Script... (it will replace the two Dev maps).

Creates
  /Game/HATI/...                         folder structure
  /Game/HATI/Blockout/Materials/MI_BO_*  color-coded, world-aligned grid materials
  /Game/HATI/Maps/Dev/L_Dev_ScaleGym     metrics gym (heights, jumps, slopes, stairs, corridors)
  /Game/HATI/Maps/Dev/L_Dev_Sandbox      empty lit floor for free blockout + color legend
"""
import math
import unreal

EAL = unreal.EditorAssetLibrary
MEL = unreal.MaterialEditingLibrary
LES = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
TOOLS = unreal.AssetToolsHelpers.get_asset_tools()

ROOT = "/Game/HATI"
FOLDERS = [
    "Maps/Dev", "Maps/Scenes",
    "Blockout/Materials", "Blockout/Meshes", "Blockout/Prefabs",
    "Environment", "Props", "PCG", "Blueprints", "Characters",
    "VFX", "Audio", "UI", "Cinematics", "Data",
]

GRID_PARENT = "/Game/_Template/LevelPrototyping/Materials/M_PrototypeGrid"
CUBE = "/Game/_Template/LevelPrototyping/Meshes/SM_Cube"

# Level-design color legend (linear colors). Grid lines are derived darker.
LEGEND = [
    # name,        surface color,            meaning (shown on the legend board)
    ("Floor",      (0.20, 0.20, 0.20),  "FLOOR - walkable ground"),
    ("Wall",       (0.05, 0.07, 0.12),  "WALL - blocking / boundary"),
    ("Path",       (0.70, 0.70, 0.66),  "PATH - main route / guidance"),
    ("Cover",      (0.35, 0.16, 0.05),  "COVER - combat cover"),
    ("Traversal",  (0.75, 0.55, 0.02),  "TRAVERSAL - climb / jump"),
    ("Hazard",     (0.60, 0.03, 0.02),  "HAZARD - pollution / danger"),
    ("Interact",   (0.02, 0.45, 0.50),  "INTERACT - objective / NPC"),
    ("Restricted", (0.22, 0.05, 0.40),  "RESTRICTED - upper tier / border"),
    ("Toxic",      (0.12, 0.40, 0.04),  "TOXIC - contaminated fluid / vent"),
    ("Prop",       (0.18, 0.12, 0.08),  "PROP - clutter / scrap"),
]


def log(msg):
    unreal.log("[HATI] " + msg)


# ---------------------------------------------------------------- folders / materials
def make_folders():
    for f in FOLDERS:
        EAL.make_directory("%s/%s" % (ROOT, f))


def make_materials():
    parent = unreal.load_asset(GRID_PARENT)
    mats = {}
    folder = ROOT + "/Blockout/Materials"
    for name, col, _ in LEGEND:
        asset_name = "MI_BO_" + name
        path = "%s/%s" % (folder, asset_name)
        mi = unreal.load_asset(path) if EAL.does_asset_exist(path) else TOOLS.create_asset(
            asset_name, folder, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
        MEL.set_material_instance_parent(mi, parent)
        surf = unreal.LinearColor(col[0], col[1], col[2], 1.0)
        line = unreal.LinearColor(col[0] * 0.35, col[1] * 0.35, col[2] * 0.35, 1.0)
        sub = unreal.LinearColor(col[0] * 0.65, col[1] * 0.65, col[2] * 0.65, 1.0)
        MEL.set_material_instance_vector_parameter_value(mi, "SurfaceColor", surf)
        MEL.set_material_instance_vector_parameter_value(mi, "GridColor", line)
        MEL.set_material_instance_vector_parameter_value(mi, "SubGridColor", sub)
        MEL.set_material_instance_scalar_parameter_value(mi, "Grid Size", 100.0)  # 1 big cell = 1 m
        MEL.set_material_instance_scalar_parameter_value(mi, "Sub Grid Number", 4.0)  # 25 cm sub cells
        MEL.update_material_instance(mi)
        EAL.save_loaded_asset(mi)
        mats[name] = mi
    log("materials ready: %d" % len(mats))
    return mats


# ---------------------------------------------------------------- placement helpers
class Builder:
    def __init__(self, mats, folder):
        self.mats = mats
        self.folder = folder
        self.mesh = unreal.load_asset(CUBE)
        bb = self.mesh.get_bounding_box()
        self.mmin = bb.min
        self.msize = unreal.Vector(bb.max.x - bb.min.x, bb.max.y - bb.min.y, bb.max.z - bb.min.z)
        self.mcenter = unreal.Vector((bb.max.x + bb.min.x) / 2, (bb.max.y + bb.min.y) / 2, (bb.max.z + bb.min.z) / 2)

    def box(self, label, center, size, mat="Floor", rot=(0, 0, 0)):
        """Place SM_Cube so its bounds become `size` (cm) centered at `center`, rotated by (pitch,yaw,roll)."""
        scale = unreal.Vector(size[0] / self.msize.x, size[1] / self.msize.y, size[2] / self.msize.z)
        r = unreal.Rotator(roll=rot[2], pitch=rot[0], yaw=rot[1])
        local_c = unreal.Vector(self.mcenter.x * scale.x, self.mcenter.y * scale.y, self.mcenter.z * scale.z)
        off = r.rotate_vector(local_c) if hasattr(r, "rotate_vector") else unreal.MathLibrary.greater_greater_vector_rotator(local_c, r)
        loc = unreal.Vector(center[0], center[1], center[2]) - off
        a = EAS.spawn_actor_from_object(self.mesh, loc, r)
        a.set_actor_scale3d(scale)
        a.static_mesh_component.set_material(0, self.mats[mat])
        a.set_actor_label(label)
        a.set_folder_path(self.folder)
        return a

    def block(self, label, minc, size, mat="Floor"):
        """Axis-aligned block given its min corner (x,y,z) and size."""
        c = (minc[0] + size[0] / 2.0, minc[1] + size[1] / 2.0, minc[2] + size[2] / 2.0)
        return self.box(label, c, size, mat)

    def text(self, txt, loc, size=40, yaw=-90, color=(255, 255, 255)):
        # yaw -90: readable when looking toward +Y (gym rows); yaw 180: looking toward +X
        a = EAS.spawn_actor_from_class(unreal.TextRenderActor, unreal.Vector(*loc), unreal.Rotator(0, 0, yaw))
        c = a.text_render
        c.set_text(txt)
        c.set_editor_property("world_size", size)
        c.set_editor_property("horizontal_alignment", unreal.HorizTextAligment.EHTA_CENTER)
        c.set_editor_property("text_render_color", unreal.Color(r=color[0], g=color[1], b=color[2], a=255))
        a.set_actor_label("TXT_" + txt.split("\n")[0][:24])
        a.set_folder_path("Labels")
        return a


def add_lighting_and_start(start=(0, 0, 120), start_yaw=0):
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
    ps = EAS.spawn_actor_from_class(unreal.PlayerStart, unreal.Vector(*start), unreal.Rotator(0, 0, start_yaw))
    ps.set_folder_path("Gameplay")


def new_map(path):
    if EAL.does_asset_exist(path):
        # Re-run: open the existing map and clear it instead of deleting the package.
        if not LES.load_level(path):
            raise RuntimeError("could not open " + path)
        actors = [a for a in EAS.get_all_level_actors() if not isinstance(a, unreal.WorldSettings)]
        EAS.destroy_actors(actors)
        return
    try:
        ok = LES.new_level(path, False)  # (asset_path, is_partitioned_world)
    except TypeError:
        ok = LES.new_level(path)
    if not ok:
        raise RuntimeError("could not create " + path)


# ---------------------------------------------------------------- maps
def build_scale_gym(mats):
    path = ROOT + "/Maps/Dev/L_Dev_ScaleGym"
    new_map(path)
    b = Builder(mats, "Gym")
    b.block("Floor", (-1000, -3000, -20), (8000, 6000, 20), "Floor")
    add_lighting_and_start((900, -2900, 120), 90)  # look toward +Y, rows face the player

    # Row A - wall / cover heights   (y = -2600)
    y = -2600
    b.text("HEIGHTS (cm)", (-200, y + 150, 520), 60)
    for i, h in enumerate([50, 100, 150, 200, 300, 400]):
        x = i * 350
        mat = "Cover" if h in (100, 150) else "Wall"
        b.block("H_%d" % h, (x, y, 0), (200, 100, h), mat)
        b.text("%d" % h, (x + 100, y - 10, h + 20), 40)
    b.text("100 low cover / 150 high cover", (900, y - 10, 470), 30, color=(255, 190, 120))

    # Row B - jump up ledges         (y = -1700)
    y = -1700
    b.text("JUMP UP (cm)", (-200, y + 150, 300), 60)
    for i, h in enumerate([25, 45, 60, 90, 120, 150]):
        x = i * 350
        b.block("Ledge_%d" % h, (x, y, 0), (200, 300, h), "Traversal")
        b.text("%d" % h, (x + 100, y - 10, h + 20), 40)

    # Row C - jump gaps              (y = -800) platforms 100 high
    y = -800
    b.text("GAPS (cm)", (-200, y + 150, 300), 60)
    x = 0
    for gap in [150, 200, 300, 400, 500]:
        b.block("GapPad_%d" % gap, (x, y, 0), (200, 300, 100), "Traversal")
        x += 200
        b.text("%d" % gap, (x + gap / 2.0, y - 10, 140), 40)
        x += gap
    b.block("GapPad_end", (x, y, 0), (200, 300, 100), "Traversal")

    # Row D - slopes                 (y = 300)
    y = 300
    b.text("SLOPES (deg)", (-200, y + 150, 300), 60)
    length = 600.0
    for i, ang in enumerate([15, 30, 45, 50]):
        x = i * 800
        rad = math.radians(ang)
        thick = 20.0
        cx = x + math.cos(rad) * length / 2.0
        cz = math.sin(rad) * length / 2.0 - math.cos(rad) * thick / 2.0
        b.box("Slope_%d" % ang, (cx, y + 150, cz), (length, 300, thick), "Path" if ang < 45 else "Hazard", rot=(ang, 0, 0))
        b.text("%d" % ang, (x + 100, y - 10, 60), 40)
    b.text("walkable limit ~44", (1300, y - 10, 470), 30, color=(255, 120, 120))

    # Row E - stairs                 (y = 1200)  8 steps, 30 cm deep
    y = 1200
    b.text("STAIRS rise (cm)", (-200, y + 150, 300), 60)
    for i, rise in enumerate([15, 20, 30, 45, 50]):
        x0 = i * 600
        for s in range(8):
            b.block("Stair_%d_%d" % (rise, s), (x0 + s * 30, y, 0), (30, 300, rise * (s + 1)), "Path")
        b.text("%d" % rise, (x0 + 120, y - 10, rise * 8 + 30), 40)

    # Row F - corridor widths & doors (y = 2100) walls 300 high, 400 deep
    y = 2100
    b.text("CORRIDOR WIDTH (cm)", (-200, y + 150, 420), 60)
    x = 0
    for w in [100, 150, 200, 300, 400]:
        b.block("CorWallA_%d" % w, (x, y, 0), (50, 400, 300), "Wall")
        b.block("CorWallB_%d" % w, (x + 50 + w, y, 0), (50, 400, 300), "Wall")
        b.text("%d" % w, (x + 50 + w / 2.0, y - 10, 320), 40)
        x += 100 + w + 150
    # door frame 100 x 220
    dx = x + 100
    b.block("Door_L", (dx, y, 0), (50, 50, 300), "Wall")
    b.block("Door_R", (dx + 150, y, 0), (50, 50, 300), "Wall")
    b.block("Door_Top", (dx, y, 220), (200, 50, 80), "Wall")
    b.text("DOOR 100x220", (dx + 100, y - 10, 320), 40)

    LES.save_current_level()
    log("saved " + path)
    return path


def build_sandbox(mats):
    path = ROOT + "/Maps/Dev/L_Dev_Sandbox"
    new_map(path)
    b = Builder(mats, "Blockout")
    b.block("Floor", (-5000, -5000, -20), (10000, 10000, 20), "Floor")
    add_lighting_and_start((0, 0, 120), 0)
    # color legend board along the back wall
    bl = Builder(mats, "Legend")
    n = len(LEGEND)
    for i, (name, _, desc) in enumerate(LEGEND):
        yy = (i - (n - 1) / 2.0) * 260
        bl.block("Legend_" + name, (1500, yy - 100, 0), (200, 200, 200), name)
        bl.text(desc.split(" - ")[0], (1490, yy, 230), 28, yaw=180)
    LES.save_current_level()
    log("saved " + path)
    return path


def main():
    make_folders()
    mats = make_materials()
    build_scale_gym(mats)
    build_sandbox(mats)
    log("DONE")
    if "-HATIQuit" in unreal.SystemLibrary.get_command_line():
        unreal.SystemLibrary.quit_editor()


main()
