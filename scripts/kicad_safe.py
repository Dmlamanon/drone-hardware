"""Shared preamble for every headless pcbnew script in this repo.

TWO JOBS, and the first one is the important one.

1. NO BLOCKING DIALOGS, EVER.

   KiCad 10's `PCB_VIA::GetWidth()` and `SetWidth()` trip a wxWidgets
   debug assert ("called without a layer argument"). In an interactive
   session that is a modal dialog. In an UNATTENDED BATCH it is a stall
   that waits forever for a click nobody is there to give, and the batch
   looks hung rather than broken.

   `wx.DisableAsserts()` turns the whole class of them off for the life
   of the process. It is called on import, before any board is touched,
   so no script can forget it. This is a hard requirement for anything
   that runs without a person watching -- it is not a convenience.

2. SAFE VIA GEOMETRY ACCESSORS.

   Suppressing the dialog is not the same as calling the API correctly,
   so use these rather than the asserting forms. KiCad 10 exposes
   `GetFrontWidth()` / `SetFrontWidth()`, which are layer-free by
   definition and do not assert. Every via in this project is a plain
   through via, so front width IS the width.

Import this before pcbnew work:

    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from kicad_safe import pcbnew, via_width, set_via_width
"""
import pcbnew  # noqa: F401  (re-exported)

try:
    import wx

    wx.DisableAsserts()
    _ASSERTS_OFF = True
except Exception:                      # noqa: BLE001
    # wx should always be present inside KiCad's own interpreter. If it is
    # not, say so loudly rather than silently running with dialogs armed.
    _ASSERTS_OFF = False
    import sys

    print("WARNING: wx.DisableAsserts() unavailable -- a debug assert could "
          "open a blocking dialog and stall an unattended run", file=sys.stderr)


def asserts_disabled():
    return _ASSERTS_OFF


def via_width(via):
    """Outer copper diameter of a via, in KiCad internal units.

    GetWidth() asserts on KiCad 10 ("called without a layer argument").
    GetFrontWidth() is the layer-free accessor and does not.
    """
    return via.GetFrontWidth()


def set_via_width(via, width_iu):
    """Set a via's outer diameter. See via_width() for why not SetWidth()."""
    via.SetFrontWidth(width_iu)


def track_width(track):
    """Width of a PCB_TRACK. Safe -- only the VIA subclass asserts -- but
    routed through here so callers never have to remember which is which."""
    if track.Type() == pcbnew.PCB_VIA_T:
        return via_width(track)
    return track.GetWidth()
