from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QTextEdit, QPushButton
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5 import QtGui
from transformers import AutoModelForCausalLM, AutoTokenizer
import sys
import torch
from threading import Event

class ChatModelWorker(QThread):
    update_text = pyqtSignal(str)
    generation_finished = pyqtSignal()

    def __init__(self, model, tokenizer, prompt, device, stop_event):
        super().__init__()
        self.model = model
        self.tokenizer = tokenizer
        self.prompt = prompt
        self.device = device
        self.stop_event = stop_event

    def run(self):
        # Ensure model is on the correct device
        self.model.to(self.device)

        # Tokenize the prompt
        inputs = self.tokenizer(
            self.prompt,
            return_tensors="pt",
            padding=True,
            truncation=True,
            return_attention_mask=True
        ).to(self.device)

        # Initialize the generated tokens
        generated_ids = inputs.input_ids
        attention_mask = inputs.attention_mask

        max_new_tokens = 200  # Adjust as needed

        # Generate tokens incrementally
        for _ in range(max_new_tokens):
            if self.stop_event.is_set():
                break  # Stop generation if stop event is set

            # Get model outputs
            outputs = self.model(
                input_ids=generated_ids,
                attention_mask=attention_mask,
            )

            # Get the next token logits
            next_token_logits = outputs.logits[:, -1, :]

            # Sample the next token (using temperature and repetition penalty)
            next_token_id = torch.multinomial(
                torch.nn.functional.softmax(next_token_logits / 0.7, dim=-1), num_samples=1
            )

            # Append the next token to the generated_ids
            generated_ids = torch.cat([generated_ids, next_token_id], dim=-1)

            # Update the attention mask
            attention_mask = torch.cat(
                [attention_mask, torch.ones((attention_mask.shape[0], 1), device=self.device)], dim=1
            )

            # Decode the new token and emit it
            new_text = self.tokenizer.decode(next_token_id[0], skip_special_tokens=True)
            self.update_text.emit(new_text)

        self.generation_finished.emit()

class ChatWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AI Chat App")

        self.chat_area = QTextEdit(self)
        self.chat_area.setReadOnly(True)

        self.input_area = QTextEdit(self)
        self.input_area.setMaximumHeight(50)

        self.send_button = QPushButton("Send", self)
        self.send_button.clicked.connect(self.send_message)

        self.stop_button = QPushButton("Stop", self)
        self.stop_button.clicked.connect(self.stop_generation)

        # Layout for the buttons
        buttons_layout = QHBoxLayout()
        buttons_layout.addWidget(self.send_button)
        buttons_layout.addWidget(self.stop_button)

        # Main layout
        layout = QVBoxLayout()
        layout.addWidget(self.chat_area)
        layout.addWidget(self.input_area)
        layout.addLayout(buttons_layout)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        self.init_model()

    def init_model(self):
        """Initialize the AI model and tokenizer."""
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model_path = "ibm-granite/granite-3.0-2b-instruct"
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_path)

        # Ensure that the pad token is set
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token

        self.model = AutoModelForCausalLM.from_pretrained(self.model_path)
        self.model.eval()

    def send_message(self):
        prompt = self.input_area.toPlainText()
        if not prompt.strip():
            return  # Ignore empty messages
        self.chat_area.append(f"User: {prompt}\n")
        self.input_area.clear()

        # Stop any ongoing generation
        self.stop_generation()

        # Create a stop event
        self.stop_event = Event()

        # Start background thread for model response
        self.worker = ChatModelWorker(
            self.model, self.tokenizer, prompt, self.device, self.stop_event
        )
        self.worker.update_text.connect(self.update_chat)
        self.worker.generation_finished.connect(self.on_generation_finished)
        self.worker.start()

    def stop_generation(self):
        # Signal the worker to stop
        if hasattr(self, 'stop_event'):
            self.stop_event.set()

    def update_chat(self, text):
        # Append the new text to the chat area
        self.chat_area.moveCursor(QtGui.QTextCursor.End)
        self.chat_area.insertPlainText(text)
        self.chat_area.moveCursor(QtGui.QTextCursor.End)

    def on_generation_finished(self):
        # Clean up resources after generation is finished
        if hasattr(self, 'stop_event'):
            del self.stop_event

    def closeEvent(self, event):
        # Ensure threads are properly closed when the window is closed
        self.stop_generation()
        event.accept()

if __name__ == "__main__":
    from blackboard import theme
    app = QApplication(sys.argv)
    theme.set_theme(app, 'dark')
    window = ChatWindow()
    window.show()
    sys.exit(app.exec_())
