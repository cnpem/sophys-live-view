def test_data_source_declare_stream(data_source_manager, qtbot):
    with qtbot.waitSignals([data_source_manager.new_data_stream] * 2, timeout=1000):
        data_source_manager.start()


def test_data_source_stream_data(data_source_manager, qtbot):
    with qtbot.waitSignals([data_source_manager.new_data_received] * 4, timeout=1000):
        data_source_manager.start()
