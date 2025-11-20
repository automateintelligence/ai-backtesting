from qse.config.factories import FactoryBase


def test_factory_logs_and_creates(caplog):
    caplog.set_level("INFO")
    factory = FactoryBase("demo", builder=lambda: object())
    obj = factory.create(prior="old")
    assert obj is not None
    assert any("Component loaded" in message for message in caplog.text.splitlines())
