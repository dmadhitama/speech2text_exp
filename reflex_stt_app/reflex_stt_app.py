import reflex as rx
from rxconfig import config
import os
import shutil
from main_demo_mod import soap_demo

class State(rx.State):
    audio_file: list[str]
    is_recording: bool = False

    def toggle_recording(self):
        self.is_recording = not self.is_recording

    async def handle_upload(self, files: list[rx.UploadFile]):
        """Handle the upload of audio file(s)."""
        for file in files:
            upload_data = await file.read()
            outfile = rx.get_upload_dir() / file.filename

            # Save the file.
            with outfile.open("wb") as file_object:
                file_object.write(upload_data)

            # Update the img var.
            self.audio_file.append(file.filename)


def transcript_form() -> rx.Component:
    color = "rgb(107,99,246)"
    return rx.card(
        rx.flex(
            rx.hstack(
                rx.vstack(
                    rx.heading(
                        "Transcript result",
                        size="4",
                        weight="bold",
                    ),
                    rx.text(
                        "The text below can be edited if needed",
                        size="2",
                    ),
                    spacing="1",
                    height="100%",
                ),
                height="100%",
                spacing="4",
                align_items="center",
                width="100%",
            ),

            rx.form.root(
                rx.flex(
                    rx.flex(
                        rx.text_area(
                            placeholder="Transcript result will appear here",
                            name="message",
                            resize="vertical",
                        ),
                        direction="column",
                        spacing="1",                 
                    ),
                    rx.form.submit(
                        rx.button("Generate SOAP"),
                        as_child=True,
                    ),
                    direction="column",
                    spacing="2",
                    width="100%",
                ),
                on_submit=lambda form_data: rx.window_alert(
                    form_data.to_string()
                ),
                reset_on_submit=False,
            ),
            width="100%",
            direction="column",
            spacing="4",
        ),
        size="3",
        width="100%",
        spacing="2",
    )

def audio_upload() -> rx.Component:
    return rx.card(
        rx.vstack(
            rx.upload(
                rx.button("Upload Audio File"),
                rx.text("Drag and drop files here or click to select files"),
                id="upload-audio",
                accept={"audio/*": [".mp3", ".wav"]},
                max_files=1,
                disabled=False,
                on_drop=State.handle_upload(
                    rx.upload_files(upload_id="upload-audio")
                ),
            ),
            rx.cond(
                State.audio_file,
                rx.audio(
                    url=rx.get_upload_url(State.audio_file[-1]),
                    controls=True,
                    width="100%",
                ),
            ),
            width="100%",
            spacing="1",
        )
    )

def index():
    return rx.container(
        rx.color_mode.button(position="top-right"),
        rx.heading(
            "STT (or Text) to SOAP",
            size="2xl",
            mb="4",
            align="center",
            weight="bold",
        ),
        
        # rx.hstack(
        #     transcript_form(),
        #     audio_upload(),

        #     spacing="2",
        #     align_items="center",
        #     width="100%",
        # ),

        rx.hstack(
            rx.vstack(
                rx.spacer(),
                transcript_form(),
                spacing="4",
                width="60%",  # Adjust this if needed
            ),
            rx.vstack(
                rx.spacer(),
                audio_upload(),
                spacing="4",
                width="40%",
            ),
            spacing="1",
            align_items="flex-start",
            width="100%",  # Ensure the hstack takes full container width
        ),
        
        max_width="1200px",
        margin="0 auto",
        padding="20px",
    )

async def api_test(item_id: int):
    return {"my_result": item_id}

app = rx.App()
app.add_page(index)
app.api.add_api_route("/test", api_test, methods=["GET"])
app.api.add_api_route("/soap_demo", soap_demo, methods=["POST"])