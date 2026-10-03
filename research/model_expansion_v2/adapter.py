"""New official checkpoints on the exact v1 typed-decision interface."""

from system1bench.decision_models import DecisionAdapter


class ExpansionAdapter(DecisionAdapter):
    """Reuse the frozen baseline interface while giving each Qwen its own ID."""

    def __init__(self, name, pin, load=True):
        assert name in {'kev_27b', 'qwen35_08b', 'qwen35_4b', 'qwen38_27b'}
        interface_name = name if name.startswith('kev') else 'qwen35_9b'
        super().__init__(interface_name, pin, load=load)
        self.name = name
        self.metadata['model'] = name
        if name.startswith('qwen'):
            self.metadata['adapter'] = 'qwen_constrained_next_token'
