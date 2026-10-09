"""Explicit original-weight Laya adaptation retaining full option descriptions."""
from research.evaluation_completion_v1.adapter import HistoricalAdapter


def get_adapter(name, pin, load=True):
    assert name in {'english', 'multilingual'}
    adapter = HistoricalAdapter(name, pin)
    import laya.common as common
    original = common.encode_text

    def encode_full_option(tokenizer, text, **kwargs):
        if kwargs.get('truncation') is True and kwargs.get('max_length') == 48:
            kwargs.pop('truncation')
            kwargs.pop('max_length')
        return original(tokenizer, text, **kwargs)

    # Process-local only: never edit the user's installed/running Laya package.
    common.encode_text = encode_full_option
    adapter.metadata.update(adapter='laya_full_option_text',
                            input_adaptation='Remove per-description 48-token truncation; unchanged tensors, ontology, order and global budgets',
                            native_interface_unchanged=False)
    return adapter
