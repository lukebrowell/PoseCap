from posecap_engine.capture import enumerate_devices


class _FakeCapture:
    def __init__(self, index: int) -> None:
        self.index = index
        self.released = False

    def isOpened(self) -> bool:
        return self.index in {0, 2}

    def get(self, prop: int) -> float:
        values = {
            _FakeCv2.CAP_PROP_FRAME_WIDTH: 640.0,
            _FakeCv2.CAP_PROP_FRAME_HEIGHT: 480.0,
            _FakeCv2.CAP_PROP_FPS: 30.0 if self.index == 0 else 0.0,
        }
        return values[prop]

    def release(self) -> None:
        self.released = True


class _FakeCv2:
    CAP_PROP_FRAME_WIDTH = 3
    CAP_PROP_FRAME_HEIGHT = 4
    CAP_PROP_FPS = 5

    @staticmethod
    def VideoCapture(index: int) -> _FakeCapture:
        return _FakeCapture(index)


def test_enumerate_devices_reports_open_camera_indices(monkeypatch) -> None:
    monkeypatch.setattr("posecap_engine.capture._load_cv2", lambda: _FakeCv2)

    devices = enumerate_devices(max_index=2)

    assert [device.index for device in devices] == [0, 2]
    assert devices[0].to_json() == {
        "index": 0,
        "name": "Camera 0",
        "width": 640,
        "height": 480,
        "fps": 30.0,
    }
    assert devices[1].fps is None
