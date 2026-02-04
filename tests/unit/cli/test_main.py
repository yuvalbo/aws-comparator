"""Tests for CLI main module."""

from unittest.mock import patch

from aws_comparator.cli.main import console, main, setup_logging


class TestSetupLogging:
    """Tests for setup_logging function."""

    @patch("aws_comparator.cli.main.logging")
    @patch("aws_comparator.cli.main.RichHandler")
    def test_setup_logging_quiet_mode(self, mock_handler, mock_logging):
        """Test quiet mode sets ERROR level."""
        mock_logging.ERROR = 40
        setup_logging(verbose=0, quiet=True)
        mock_logging.basicConfig.assert_called_once()
        call_kwargs = mock_logging.basicConfig.call_args[1]
        assert call_kwargs["level"] == 40

    @patch("aws_comparator.cli.main.logging")
    @patch("aws_comparator.cli.main.RichHandler")
    def test_setup_logging_default(self, mock_handler, mock_logging):
        """Test default mode sets WARNING level."""
        mock_logging.WARNING = 30
        setup_logging(verbose=0, quiet=False)
        mock_logging.basicConfig.assert_called_once()
        call_kwargs = mock_logging.basicConfig.call_args[1]
        assert call_kwargs["level"] == 30

    @patch("aws_comparator.cli.main.logging")
    @patch("aws_comparator.cli.main.RichHandler")
    def test_setup_logging_verbose_1(self, mock_handler, mock_logging):
        """Test verbose=1 sets INFO level."""
        mock_logging.INFO = 20
        setup_logging(verbose=1, quiet=False)
        mock_logging.basicConfig.assert_called_once()
        call_kwargs = mock_logging.basicConfig.call_args[1]
        assert call_kwargs["level"] == 20

    @patch("aws_comparator.cli.main.logging")
    @patch("aws_comparator.cli.main.RichHandler")
    def test_setup_logging_verbose_2(self, mock_handler, mock_logging):
        """Test verbose=2 sets DEBUG level."""
        mock_logging.DEBUG = 10
        setup_logging(verbose=2, quiet=False)
        mock_logging.basicConfig.assert_called_once()
        call_kwargs = mock_logging.basicConfig.call_args[1]
        assert call_kwargs["level"] == 10

    @patch("aws_comparator.cli.main.logging")
    @patch("aws_comparator.cli.main.RichHandler")
    def test_setup_logging_verbose_3(self, mock_handler, mock_logging):
        """Test verbose=3 sets DEBUG level with extras."""
        mock_logging.DEBUG = 10
        setup_logging(verbose=3, quiet=False)
        mock_logging.basicConfig.assert_called_once()
        call_kwargs = mock_logging.basicConfig.call_args[1]
        assert call_kwargs["level"] == 10

    @patch("aws_comparator.cli.main.logging")
    @patch("aws_comparator.cli.main.RichHandler")
    def test_setup_logging_configures_rich_handler(self, mock_handler, mock_logging):
        """Test that RichHandler is configured."""
        mock_logging.WARNING = 30
        setup_logging(verbose=0, quiet=False)
        mock_handler.assert_called_once()


class TestMain:
    """Tests for main function."""

    @patch("aws_comparator.cli.main.cli")
    def test_main_success(self, mock_cli):
        """Test main function runs CLI successfully."""
        mock_cli.return_value = None
        # Should not raise
        main()
        mock_cli.assert_called_once_with(standalone_mode=True)

    @patch("aws_comparator.cli.main.cli")
    @patch("aws_comparator.cli.main.sys.exit")
    @patch("aws_comparator.cli.main.console")
    def test_main_keyboard_interrupt(self, mock_console, mock_exit, mock_cli):
        """Test main handles KeyboardInterrupt."""
        mock_cli.side_effect = KeyboardInterrupt()
        main()
        mock_exit.assert_called_once_with(130)
        mock_console.print.assert_called()

    @patch("aws_comparator.cli.main.cli")
    @patch("aws_comparator.cli.main.sys.exit")
    @patch("aws_comparator.cli.main.console")
    def test_main_unexpected_exception(self, mock_console, mock_exit, mock_cli):
        """Test main handles unexpected exceptions."""
        mock_cli.side_effect = RuntimeError("Unexpected error")
        main()
        mock_exit.assert_called_once_with(1)
        mock_console.print.assert_called()


class TestConsole:
    """Tests for console instance."""

    def test_console_is_rich_console(self):
        """Test console is a Rich Console instance."""
        from rich.console import Console

        assert isinstance(console, Console)


class TestModuleExports:
    """Tests for module exports."""

    def test_all_exports(self):
        """Test __all__ contains expected exports."""
        from aws_comparator.cli import main as main_module

        assert "cli" in main_module.__all__
        assert "console" in main_module.__all__
        assert "main" in main_module.__all__
        assert "setup_logging" in main_module.__all__
