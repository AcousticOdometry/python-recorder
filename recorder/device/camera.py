# def find_cameras(max_index: int = 10) -> dict:
#     return {
#         i: {
#             'cap':
#                 cap,
#             'name':
#                 cv2.videoio_registry.getBackendName(
#                     int(cap.get(cv2.CAP_PROP_BACKEND))
#                     ),
#             'width':
#                 int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
#             'height':
#                 int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
#             }
#         for i in range(max_index) if (cap := cv2.VideoCapture(i)).isOpened()
#         }

# Camera = Device(find_cameras, 'camera')

# @app.command(help='Display the available cameras')
# def show_cameras():
#     # Remove the `cap` attribute from the camera devices
#     devices = {
#         i: {k: v
#             for k, v in camera.items() if k != 'cap'}
#         for i, camera in Camera.find().items()
#         }
#     typer.echo('Real Sense devices:\n' + yaml_dump(devices))

