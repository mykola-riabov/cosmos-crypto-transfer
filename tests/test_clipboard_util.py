import unittest
from unittest.mock import MagicMock, patch

from gui.clipboard_util import copy_to_clipboard


class TestClipboardUtil(unittest.TestCase):
    def test_copy_tk_success(self):
        widget = MagicMock()
        widget.clipboard_clear = MagicMock()
        widget.clipboard_append = MagicMock()
        widget.update_idletasks = MagicMock()
        widget.after = MagicMock()
        with patch('gui.clipboard_util.sys.platform', 'darwin'):
            self.assertTrue(copy_to_clipboard(widget, 'osmo1abc'))
        widget.clipboard_append.assert_called()

    @patch('gui.clipboard_util.shutil.which', return_value='/usr/bin/wl-copy')
    @patch('gui.clipboard_util.subprocess.run')
    def test_copy_linux_fallback(self, mock_run, _which):
        widget = MagicMock()
        import tkinter as tk

        widget.clipboard_clear = MagicMock(side_effect=tk.TclError('fail'))
        widget.clipboard_append = MagicMock(side_effect=tk.TclError('fail'))
        widget.after = MagicMock()
        with patch('gui.clipboard_util.sys.platform', 'linux'):
            self.assertTrue(copy_to_clipboard(widget, 'osmo1abc'))
        mock_run.assert_called()


if __name__ == '__main__':
    unittest.main()
