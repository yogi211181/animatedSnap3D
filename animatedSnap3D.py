# path: ~/.nuke/animatedSnap3D.py
import nuke
from nukescripts import snap3d as s3d

def _get_frame_range():
    first_frame = int(nuke.numvalue("root.first_frame"))
    last_frame = int(nuke.numvalue("root.last_frame"))
    default_range = f"{first_frame}-{last_frame}x1"
    user = nuke.getInput("Enter Frame Range:", default_range)
    if not user:
        return None
    try:
        return nuke.FrameRange(user)
    except Exception:
        nuke.message("Invalid frame range")
        return None

def _resolve_target_node(required_knobs):
    """Why: main-menu invocations lack thisNode; prefer a selected transform node."""
    # prefer selected nodes that have the right knobs
    for node in nuke.selectedNodes():
        if all(node.knob(k) is not None for k in required_knobs):
            return node
    # fallback to thisNode when valid
    try:
        tn = nuke.thisNode()
    except Exception:
        tn = None
    if tn and all(tn.knob(k) is not None for k in required_knobs):
        return tn
    nuke.message(
        'Select a transformable node (Axis, Camera, Card, TransformGeo, Light) then run.\n'
        f"Missing knobs: {required_knobs}"
    )
    return None

# -------- Public commands (now resolve node from selection) --------
def translateToPointsAnimated():
    knobs_to_verify = ["translate", "xform_order"]
    node_to_snap = _resolve_target_node(knobs_to_verify)
    if not node_to_snap:
        return
    return _animated_snap(
        node_to_snap,
        knobs_to_animate=["translate"],
        knobs_to_verify=knobs_to_verify,
        min_vertices=1,
        snap_func=s3d.translateToPointsVerified,
    )

def translateRotateToPointsAnimated():
    knobs_to_verify = ["translate", "rotate", "xform_order", "rot_order"]
    node_to_snap = _resolve_target_node(knobs_to_verify)
    if not node_to_snap:
        return
    return _animated_snap(
        node_to_snap,
        knobs_to_animate=["translate", "rotate"],
        knobs_to_verify=knobs_to_verify,
        min_vertices=1,
        snap_func=s3d.translateRotateToPointsVerified,
    )

def translateRotateScaleToPointsAnimated():
    knobs_to_verify = ["translate", "rotate", "scaling", "xform_order", "rot_order"]
    node_to_snap = _resolve_target_node(knobs_to_verify)
    if not node_to_snap:
        return
    return _animated_snap(
        node_to_snap,
        knobs_to_animate=["translate", "rotate", "scaling"],
        knobs_to_verify=knobs_to_verify,
        min_vertices=3,
        snap_func=s3d.translateRotateScaleToPointsVerified,
    )

# -------- Core loop --------
def _animated_snap(node_to_snap, knobs_to_animate, knobs_to_verify, min_vertices, snap_func):
    temp = None
    try:
        s3d.verifyNodeToSnap(node_to_snap, knobs_to_verify)
        sel = s3d.getSelection()
        s3d.verifyVertexSelection(sel, min_vertices)

        frames = _get_frame_range()
        if not frames:
            return

        temp = nuke.nodes.CurveTool()  # Why: forces DAG eval per frame.

        for name in knobs_to_animate:
            k = node_to_snap[name]
            if k.isAnimated():
                k.clearAnimated()
            k.setAnimated()

        task = nuke.ProgressTask("animatedSnap3D")
        task.setMessage(f"Snapping {node_to_snap.name()}")

        for f in frames:
            if task.isCancelled():
                break
            nuke.execute(temp, int(f), int(f))  # force evaluation at time
            current_sel = s3d.getSelection()
            s3d.verifyVertexSelection(current_sel, min_vertices)
            snap_func(node_to_snap, current_sel)
    except ValueError as e:
        nuke.message(str(e))
    finally:
        if temp:
            nuke.delete(temp)

# -------- Menu registration --------
def add_to_menu():
    m = nuke.menu("Nuke").addMenu("Animated Snap3D")
    m.addCommand("Translate to Points (Animated)", "animatedSnap3D.translateToPointsAnimated()")
    m.addCommand("Translate+Rotate to Points (Animated)", "animatedSnap3D.translateRotateToPointsAnimated()")
    m.addCommand("Translate+Rotate+Scale to Points (Animated)", "animatedSnap3D.translateRotateScaleToPointsAnimated()")
