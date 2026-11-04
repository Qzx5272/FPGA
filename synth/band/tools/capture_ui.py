"""Render the app's own widgets offscreen for layout review; opens no ports."""
import os,sys
from pathlib import Path
os.environ['QT_QPA_PLATFORM']='offscreen'
band=Path(__file__).resolve().parents[1];sys.path.insert(0,str(band/'host'))
from app import QApplication,Desk
from PySide6.QtWidgets import QScrollArea,QToolButton
out=band/'evidence/ui';out.mkdir(exist_ok=True)
app=QApplication([]);desk=Desk();desk.show();app.processEvents()
desk.grab().save(str(out/'desk_top.png'))
scroll=desk.findChild(QScrollArea);scroll.verticalScrollBar().setValue(scroll.verticalScrollBar().maximum());app.processEvents();desk.grab().save(str(out/'desk_controls.png'))
desk.open_editor();app.processEvents();desk.editor.grab().save(str(out/'editor.png'))
for button in desk.editor.findChildren(QToolButton):
 if button.text()=='导出脱机工程':
  menu=button.menu();menu.popup(button.mapToGlobal(button.rect().bottomLeft()));app.processEvents()
  menu.grab().save(str(out/'editor_export_menu.png'));menu.hide()
desk.editor.part.setCurrentIndex(7);desk.editor.bar.setValue(25);app.processEvents();desk.editor.grab().save(str(out/'editor_choir.png'))
desk.open_patch();app.processEvents();desk.patch_editor.grab().save(str(out/'patch.png'))
desk.open_calibration();app.processEvents();desk.calibration_editor.grab().save(str(out/'calibration.png'))
desk.open_stage();app.processEvents();desk.stage_view.grab().save(str(out/'stage_disconnected.png'))
desk.close();print(out)
