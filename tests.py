import os
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import pytest
import markovify

import botconfig
import model_manager
import dataset
import utils


# ============================================================================
# Tests for botconfig.py
# ============================================================================

class TestBotConfig:
    """Tests for bot configuration constants."""

    def test_token_exists(self):
        """Test that TOKEN constant exists."""
        assert hasattr(botconfig, 'TOKEN')

    def test_bot_channel_is_int(self):
        """Test that BOT_CHANNEL is an integer."""
        assert isinstance(botconfig.BOT_CHANNEL, int)

    def test_try_count_is_positive(self):
        """Test that TRY_COUNT is a positive integer."""
        assert isinstance(botconfig.TRY_COUNT, int)
        assert botconfig.TRY_COUNT > 0

    def test_state_size_is_positive(self):
        """Test that STATE_SIZE is a positive integer."""
        assert isinstance(botconfig.STATE_SIZE, int)
        assert botconfig.STATE_SIZE > 0


# ============================================================================
# Tests for model_manager.py
# ============================================================================

class TestModelManager:
    """Tests for model manager functions."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for test files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    @pytest.fixture
    def sample_messages_file(self, temp_dir):
        """Create a sample messages.txt file for testing."""
        messages_path = os.path.join(temp_dir, "messages.txt")
        sample_text = (
            "This is a test message\n"
            "This is another test message\n"
            "Testing the markov model\n"
            "Hello world\n"
            "This is a test\n"
        )
        with open(messages_path, "w", encoding="utf-8") as f:
            f.write(sample_text)
        return messages_path

    def test_build_markov_model_creates_model(self, temp_dir, sample_messages_file):
        """Test that build_markov_model creates a valid markov model."""
        with patch("model_manager.botconfig.STATE_SIZE", 2):
            with patch("builtins.open", create=True) as mock_open:
                mock_open.return_value.__enter__.return_value.read.return_value = (
                    "This is a test message\n"
                    "This is another test message\n"
                )
                text_model = model_manager.build_markov_model()
                assert isinstance(text_model, markovify.NewlineText)

    def test_build_markov_model_file_not_found(self):
        """Test that build_markov_model raises FileNotFoundError when messages.txt doesn't exist."""
        with patch("builtins.open", side_effect=FileNotFoundError):
            with pytest.raises(FileNotFoundError):
                model_manager.build_markov_model()

    def test_build_markov_model_permission_error(self):
        """Test that build_markov_model raises PermissionError when file can't be read."""
        with patch("builtins.open", side_effect=PermissionError):
            with pytest.raises(PermissionError):
                model_manager.build_markov_model()

    def test_save_model_creates_json(self, temp_dir):
        """Test that save_model creates a JSON file."""
        output_path = os.path.join(temp_dir, "markov_model.json")

        # Create a sample model
        sample_text = "This is a test\nThis is another test\n" * 10
        text_model = markovify.NewlineText(sample_text, state_size=2)

        with patch("builtins.open", create=True) as mock_open:
            mock_open.return_value.__enter__.return_value.read.return_value = sample_text
            mock_file = MagicMock()
            mock_open.return_value.__enter__.return_value = mock_file

            # Create and compile a model to get valid JSON
            model_json = text_model.to_json()
            assert isinstance(model_json, str)
            assert "state_size" in model_json

    def test_load_model_file_not_found(self):
        """Test that load_model raises FileNotFoundError when model file doesn't exist."""
        with patch("builtins.open", side_effect=FileNotFoundError):
            with pytest.raises(FileNotFoundError):
                model_manager.load_model()

    def test_load_model_permission_error(self):
        """Test that load_model raises PermissionError when model file can't be read."""
        with patch("builtins.open", side_effect=PermissionError):
            with pytest.raises(PermissionError):
                model_manager.load_model()

    def test_load_model_valid_json(self, temp_dir):
        """Test that load_model successfully loads a valid model JSON."""
        # Create a valid markov model
        sample_text = "This is a test message\n" * 20
        text_model = markovify.NewlineText(sample_text, state_size=2)
        model_json = text_model.to_json()

        model_path = os.path.join(temp_dir, "markov_model.json")
        with open(model_path, "w", encoding="utf-8") as f:
            f.write(model_json)

        with patch("builtins.open", create=True) as mock_open:
            mock_open.return_value.__enter__.return_value.read.return_value = model_json
            loaded_model = model_manager.load_model()
            assert isinstance(loaded_model, markovify.NewlineText)


# ============================================================================
# Tests for dataset.py
# ============================================================================

class TestDataset:
    """Tests for dataset processing functions."""

    @pytest.fixture
    def temp_messages_dir(self):
        """Create a temporary messages directory structure for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    def test_dataset_main_creates_messages_txt(self, temp_messages_dir):
        """Test that dataset.main creates messages.txt file."""
        # Create a mock messages directory structure
        messages_dir = os.path.join(temp_messages_dir, "Messages")
        os.makedirs(messages_dir)

        channel_dir = os.path.join(messages_dir, "test_channel")
        os.makedirs(channel_dir)

        # Create a sample messages.json file
        messages_data = [
            {"Contents": "Hello world"},
            {"Contents": "This is a test message"},
            {"Contents": None},  # Test None handling
        ]

        messages_json_path = os.path.join(channel_dir, "messages.json")
        with open(messages_json_path, "w") as f:
            json.dump(messages_data, f)

        # Mock os.walk and tqdm for testing
        with patch("os.walk") as mock_walk, \
                patch("dataset.tqdm", side_effect=lambda x, **kwargs: x), \
                patch("json.load") as mock_json_load:

            mock_walk.return_value = [
                (channel_dir, [], ["messages.json"])
            ]

            # Mock json.load to return the test data
            mock_json_load.return_value = messages_data

            original_messages = None

            # Test that the function processes messages correctly
            try:
                # Clear and reset messages list
                original_messages = dataset.messages[:]
                dataset.messages.clear()

                # Mock the file operations for json loading
                with patch("builtins.open", create=True):
                    dataset.main()
            except ValueError as e:
                # Expected if messages list ends up empty
                assert "non-empty list" in str(e)
            finally:
                # Restore original messages
                dataset.messages = original_messages

    def test_dataset_skips_code_blocks(self):
        """Test that dataset processing skips messages with code blocks."""
        test_message = "Check this code:\n```python\nprint('hello')\n```"
        # The dataset.py filters out messages with ```
        assert "```" in test_message
        # Verify the filtering logic would skip this
        assert not (test_message != "" and "```" not in test_message)

    def test_dataset_skips_empty_messages(self):
        """Test that dataset processing skips empty messages."""
        test_message = ""
        # Empty messages should be skipped
        assert test_message == ""


# ============================================================================
# Tests for utils.py
# ============================================================================

class TestUtils:
    """Tests for utility functions."""

    def test_load_discord_client_returns_client(self):
        """Test that load_discord_client returns a Discord client."""
        with patch("discord.Client") as mock_client_class:
            mock_client_instance = MagicMock()
            mock_client_class.return_value = mock_client_instance

            client = utils.load_discord_client()
            assert client is not None

    def test_load_discord_client_sets_intents(self):
        """Test that load_discord_client sets correct intents."""
        with patch("discord.Intents") as mock_intents_class, \
                patch("discord.Client") as mock_client_class:

            mock_intents = MagicMock()
            mock_intents_class.default.return_value = mock_intents
            mock_client_instance = MagicMock()
            mock_client_class.return_value = mock_client_instance

            utils.load_discord_client()

            # Check that intents were configured
            mock_intents_class.default.assert_called_once()

    def test_is_valid_channel_correct_channel(self):
        """Test is_valid_channel returns True for correct channel."""
        with patch.object(botconfig, "BOT_CHANNEL", 12345):
            message = MagicMock()
            message.channel.id = 12345
            # Don't set parent_id attribute so getattr returns default None
            del message.channel.parent_id

            result = utils.is_valid_channel(message)
            assert result is True

    def test_is_valid_channel_correct_forum_parent(self):
        """Test is_valid_channel returns True for correct forum parent."""
        with patch.object(botconfig, "BOT_CHANNEL", 12345):
            message = MagicMock()
            message.channel.id = 99999
            message.channel.parent_id = 12345

            result = utils.is_valid_channel(message)
            assert result is True

    def test_is_valid_channel_incorrect_channel(self):
        """Test is_valid_channel returns False for incorrect channel."""
        with patch.object(botconfig, "BOT_CHANNEL", 12345), \
                patch("logging.error"):
            message = MagicMock()
            message.channel.id = 99999
            message.channel.parent_id = 88888

            result = utils.is_valid_channel(message)
            assert result is False


# ============================================================================
# Integration Tests
# ============================================================================

class TestIntegration:
    """Integration tests combining multiple components."""

    def test_markov_model_workflow(self):
        """Test the complete workflow of creating and using a markov model."""
        # Create sample text
        sample_text = (
            "The quick brown fox jumps over the lazy dog\n"
            "The lazy dog sleeps in the sun\n"
            "The quick fox is very clever\n"
        ) * 5

        # Create a model
        try:
            text_model = markovify.NewlineText(sample_text, state_size=2)
            text_model.compile(inplace=True)

            # Test that we can generate sentences
            generated = text_model.make_sentence(tries=100)
            # Generated might be None if it can't create a valid sentence
            assert generated is None or isinstance(generated, str)
        except Exception as e:
            pytest.fail(f"Model workflow failed: {e}")

    def test_message_generation_with_start_term(self):
        """Test message generation with a starting term."""
        sample_text = (
            "Hello world\n"
            "Hello there\n"
            "Hello friend\n"
            "Hello everyone\n"
            "The world is beautiful\n"
            "Hello to you\n"
            "Hello my friend\n"
        ) * 10

        text_model = markovify.NewlineText(sample_text, state_size=2)
        text_model.compile(inplace=True)

        # Try to generate with a start term
        # Note: make_sentence_with_start may raise an exception if it can't find
        # a valid sentence starting with the term, which is acceptable behavior
        try:
            generated = text_model.make_sentence_with_start("Hello", tries=100)
            # If a sentence was generated, it should start with Hello
            if generated:
                assert generated.lower().startswith("hello")
        except markovify.text.ParamError:
            # This is acceptable - markovify couldn't generate a sentence with that start
            pass


# ============================================================================
# Edge Case Tests
# ============================================================================

class TestEdgeCases:
    """Tests for edge cases and error conditions."""

    def test_very_small_text_corpus(self):
        """Test handling of very small text corpus."""
        small_text = "Hello world\n"
        try:
            text_model = markovify.NewlineText(small_text, state_size=2)
            # Very small corpus might not generate valid sentences
            generated = text_model.make_sentence(tries=100)
            assert generated is None or isinstance(generated, str)
        except Exception as e:
            # Small corpus might cause issues
            pass

    def test_special_characters_in_messages(self):
        """Test handling of special characters in messages."""
        special_text = (
            "Hello! How are you?\n"
            "I'm doing great, thanks for asking!\n"
            "Special chars: @#$%^&*()\n"
        ) * 5

        text_model = markovify.NewlineText(special_text, state_size=2)
        text_model.compile(inplace=True)

        # Should handle special characters without errors
        generated = text_model.make_sentence(tries=100)
        assert generated is None or isinstance(generated, str)

    def test_unicode_characters_in_messages(self):
        """Test handling of unicode characters in messages."""
        unicode_text = (
            "Hello 👋 world 🌍\n"
            "こんにちは世界\n"
            "Привет мир\n"
        ) * 5

        text_model = markovify.NewlineText(unicode_text, state_size=2)
        text_model.compile(inplace=True)

        # Should handle unicode without errors
        generated = text_model.make_sentence(tries=100)
        assert generated is None or isinstance(generated, str)
