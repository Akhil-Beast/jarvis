import time
import uiautomation as auto
from core.safety import logger

class UIAController:
    """Controls Windows UI elements via Microsoft UI Automation Accessibility Framework."""

    def __init__(self):
        auto.SetGlobalSearchTimeout(1.5)

    @staticmethod
    def get_focused_window():
        """Returns the UIA Control for the current foreground window."""
        try:
            return auto.GetForegroundControl()
        except Exception:
            return None

    def click_element_by_name(self, name: str, control_type: str = "") -> bool:
        """Finds a button or control by its text/name in the active window and clicks it."""
        fg = self.get_focused_window()
        if not fg:
            fg = auto.GetRootControl()

        name_clean = name.strip()
        logger.info(f"[UIA] Searching for element '{name_clean}' (type={control_type})...")

        try:
            # 1. Look for Button
            btn = fg.ButtonControl(searchDepth=8, SubName=name_clean)
            if btn.Exists(maxSearchSeconds=1.0):
                logger.info(f"[UIA] Found button '{btn.Name}', invoking...")
                if hasattr(btn, "Invoke") and btn.GetInvokePattern():
                    btn.Invoke()
                else:
                    btn.Click()
                return True

            # 2. Look for MenuItem
            menu = fg.MenuItemControl(searchDepth=8, SubName=name_clean)
            if menu.Exists(maxSearchSeconds=1.0):
                logger.info(f"[UIA] Found menu item '{menu.Name}', clicking...")
                menu.Click()
                return True

            # 3. Look for generic Control by SubName
            ctrl = fg.Control(searchDepth=8, SubName=name_clean)
            if ctrl.Exists(maxSearchSeconds=1.0):
                logger.info(f"[UIA] Found control '{ctrl.Name}', clicking...")
                ctrl.Click()
                return True

        except Exception as e:
            logger.warning(f"[UIA] Error during element click: {e}")

        logger.warning(f"[UIA] Element '{name}' could not be found.")
        return False

    def type_into_field(self, field_name: str, text: str) -> bool:
        """Finds an edit box/input field and sets or types text into it."""
        fg = self.get_focused_window()
        if not fg:
            fg = auto.GetRootControl()

        try:
            edit = None
            if field_name:
                edit = fg.EditControl(searchDepth=8, SubName=field_name)
            if not edit or not edit.Exists(0.5):
                # Fallback to the currently focused edit control or first edit control
                edit = fg.EditControl(searchDepth=8)

            if edit and edit.Exists(maxSearchSeconds=1.0):
                edit.Click()
                time.sleep(0.1)
                try:
                    edit.GetValuePattern().SetValue(text)
                except Exception:
                    edit.SendKeys(text)
                logger.info(f"[UIA] Set text into field '{edit.Name}'")
                return True
        except Exception as e:
            logger.warning(f"[UIA] Error typing into field: {e}")

        return False

    def get_visible_ui_summary(self, max_elements: int = 25) -> list[dict]:
        """Summarizes visible interactable elements in the active window for the AI planner."""
        summary = []
        fg = self.get_focused_window()
        if not fg:
            return summary

        try:
            for child, depth in auto.WalkControl(fg, maxDepth=4):
                if not child.IsOffscreen and child.Name:
                    ctype = child.ControlTypeName
                    if ctype in ["ButtonControl", "MenuItemControl", "EditControl", "TabItemControl", "HyperlinkControl"]:
                        summary.append({
                            "type": ctype.replace("Control", ""),
                            "name": child.Name.strip(),
                            "id": child.AutomationId
                        })
                        if len(summary) >= max_elements:
                            break
        except Exception as e:
            logger.warning(f"[UIA] Error walking UI tree: {e}")

        return summary

uia_controller = UIAController()
