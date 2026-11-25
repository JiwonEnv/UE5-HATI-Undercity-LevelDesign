"""
HATI : Undercity - one-time Content folder reorganization (2026-11-25).

Moves the UE template folders under /Game/_Template so /Game holds only HATI and _Template:
  /Game/Characters       -> /Game/_Template/Characters
  /Game/Input            -> /Game/_Template/Input
  /Game/LevelPrototyping -> /Game/_Template/LevelPrototyping
  /Game/ThirdPerson      -> /Game/_Template/ThirdPerson
then fixes up every redirector the move left behind (maps and World Partition actors that
referenced the moved assets are re-saved pointing at the new paths) and deletes the old folders.

Safe to re-run: folders that are already moved are skipped.
  UnrealEditor.exe HATI_Undercity.uproject -ExecutePythonScript="Tools/reorganize_content.py"
"""
import unreal

EAL = unreal.EditorAssetLibrary
TOOLS = unreal.AssetToolsHelpers.get_asset_tools()
AR = unreal.AssetRegistryHelpers.get_asset_registry()

MOVES = [
    ("/Game/Characters", "/Game/_Template/Characters"),
    ("/Game/Input", "/Game/_Template/Input"),
    ("/Game/LevelPrototyping", "/Game/_Template/LevelPrototyping"),
    ("/Game/ThirdPerson", "/Game/_Template/ThirdPerson"),
]


def log(m):
    unreal.log("[HATI-REORG] " + m)


def warn(m):
    unreal.log_warning("[HATI-REORG] " + m)


def find_redirectors():
    f = unreal.ARFilter(
        class_paths=[unreal.TopLevelAssetPath("/Script/CoreUObject", "ObjectRedirector")],
        package_paths=["/Game"], recursive_paths=True)
    return AR.get_assets(f)


def pending(src, dst):
    """Assets under `src` not yet present under `dst` (what is left at `src` after a move is redirectors)."""
    out = []
    for p in EAL.list_assets(src, True, False):
        pkg = p.split(".")[0]
        if EAL.does_asset_exist(dst + pkg[len(src):]):
            continue
        out.append((p, EAL.find_asset_data(p)))
    return out


def move_world(obj_path, src, dst):
    """World Partition maps can't be renamed in place: Save As to the new path, then delete the old one."""
    pkg = obj_path.split(".")[0]
    new_pkg = dst + pkg[len(src):]
    les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    if not les.load_level(pkg):
        return False
    ues = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    if not unreal.EditorLoadingAndSavingUtils.save_map(ues.get_editor_world(), new_pkg):
        return False
    les.load_level("/Game/HATI/Maps/Dev/L_Dev_Sandbox")
    ok = EAL.delete_asset(pkg)
    log("  map %s -> %s (old deleted: %s)" % (pkg, new_pkg, ok))
    return True


def move_one_by_one(src, dst):
    ok = True
    for p, d in pending(src, dst):
        pkg = p.split(".")[0]
        new_pkg = dst + pkg[len(src):]
        if d.asset_class_path.asset_name == "World":
            ok = move_world(p, src, dst) and ok
        else:
            r = EAL.rename_asset(pkg, new_pkg)
            log("  %s -> %s : %s" % (pkg, new_pkg, r))
            ok = r and ok
    return ok


def main():
    AR.search_all_assets(True)
    EAL.make_directory("/Game/_Template")
    for src, dst in MOVES:
        assets = pending(src, dst) if EAL.does_directory_exist(src) else []
        if not assets:
            log("skip %s (nothing left to move)" % src)
            continue
        ok = (not EAL.does_directory_exist(dst)) and EAL.rename_directory(src, dst)
        log("%s -> %s : %s (%d assets)" % (src, dst, "OK" if ok else "moving one by one", len(assets)))
        if not ok and not move_one_by_one(src, dst):
            warn("move failed for %s, stopping" % src)
            return

    consolidate_leftovers()
    resave_referencers()
    resave_assets_mentioning_old_paths()
    # The redirector files themselves are deleted from disk after the editor closes
    # (see the PowerShell step in the PR); deleting them here could resolve to the moved asset.
    log("DONE")


def is_redirector(pkg):
    for d in AR.get_assets_by_package_name(pkg) or []:
        if d.asset_class_path.asset_name == "ObjectRedirector":
            return True
    return False


def consolidate_leftovers():
    """Assets that were loaded while being moved (e.g. the mannequin mesh/textures) can't have their old
    file overwritten by a redirector, so a full copy stays at the old path. Merge each such copy into
    its twin under _Template: references are pointed at the twin and the old copy is deleted."""
    AR.search_all_assets(True)
    for src, dst in MOVES:
        if not EAL.does_directory_exist(src):
            continue
        for p in EAL.list_assets(src, True, False):
            pkg = p.split(".")[0]
            twin = dst + pkg[len(src):]
            if is_redirector(pkg) or not EAL.does_asset_exist(twin):
                continue
            old_obj = unreal.load_asset(pkg)
            new_obj = unreal.load_asset(twin)
            if not old_obj or not new_obj or old_obj == new_obj:
                warn("cannot consolidate %s" % pkg)
                continue
            ok = EAL.consolidate_assets(new_obj, [old_obj])
            log("consolidate %s -> %s : %s" % (pkg, twin, ok))
    unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)


def resave_assets_mentioning_old_paths():
    """The asset registry can lag behind, so also scan the files: any non-map asset whose bytes still
    contain an old folder path is loaded and saved again (loading resolves redirectors)."""
    import os
    content = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_content_dir())
    old = [s.encode() + b"/" for s, _ in MOVES]
    for root_rel in ("HATI", "_Template"):
        for root, _, files in os.walk(os.path.join(content, root_rel)):
            for fn in files:
                if not fn.endswith(".uasset"):
                    continue
                full = os.path.join(root, fn)
                with open(full, "rb") as fh:
                    data = fh.read()
                if not any(o in data for o in old):
                    continue
                rel = os.path.relpath(full, content).replace("\\", "/")[:-len(".uasset")]
                obj = unreal.load_asset("/Game/" + rel)
                ok = obj is not None and EAL.save_loaded_asset(obj, False)
                log("re-saved (old path in file) /Game/%s : %s" % (rel, ok))


def map_of(pkg):
    """Owning map of a package: an external actor package maps to its level, a map to itself."""
    pkg = str(pkg)
    for root in ("/Game/__ExternalActors__/", "/Game/__ExternalObjects__/"):
        if pkg.startswith(root):
            parts = pkg[len(root):].split("/")
            return "/Game/" + "/".join(parts[:-3]), pkg   # strip the 3 hashed sub-folders
    return pkg, None


def resave_referencers():
    """Python has no FixupReferencers, so: open every map that references a redirector, touch the
    referencing actors (or the level itself), and save. Loading resolves the redirector, saving
    writes the new path."""
    opt = unreal.AssetRegistryDependencyOptions(include_soft_package_references=True, include_hard_package_references=True)
    AR.search_all_assets(True)
    todo = {}
    assets = set()
    for r in find_redirectors():
        for ref in AR.get_referencers(r.package_name, opt) or []:
            m, ext = map_of(ref)
            if not str(m).startswith("/Game/") or is_redirector(str(m)):
                continue
            datas = AR.get_assets_by_package_name(m) or []
            if not ext and datas and datas[0].asset_class_path.asset_name != "World":
                assets.add(str(m))       # a regular asset (BP, mesh...): load + resave
                continue
            todo.setdefault(m, set())
            if ext:
                todo[m].add(ext)
    for a in sorted(assets):
        obj = unreal.load_asset(a)
        ok = obj and EAL.save_loaded_asset(obj, False)
        log("re-saved asset %s : %s" % (a, ok))
    log("maps to re-save: %s" % sorted(todo))
    les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    for m, ext_pkgs in sorted(todo.items()):
        if not EAL.does_asset_exist(m):
            warn("skip %s (not a map asset)" % m)
            continue
        if not les.load_level(m):
            warn("could not open %s" % m)
            continue
        touched = 0
        for a in eas.get_all_level_actors():
            pkg = a.get_package().get_name()
            if (ext_pkgs and pkg in ext_pkgs) or (not ext_pkgs and pkg == m):
                a.modify()
                touched += 1
        les.save_current_level()
        unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
        log("re-saved %s (touched %d actors)" % (m, touched))
    les.load_level("/Game/HATI/Maps/Dev/L_Dev_Sandbox")
    left = []
    for r in find_redirectors():
        refs = [x for x in (AR.get_referencers(r.package_name, opt) or []) if str(x).startswith("/Game/")]
        if refs:
            left.append((r.package_name, refs))
    log("redirectors still referenced: %d" % len(left))
    for p, refs in left:
        warn("  %s <- %s" % (p, refs))


main()
