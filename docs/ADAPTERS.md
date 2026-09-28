# Adapter contract

The CLI loads `module:Class`. Construct it as `Class(model_name, checkpoint)`.
Implement these members:

```python
metadata: dict  # JSON-safe model/API version, immutable hash/revision if available
def synchronize(self): ...  # synchronize device work; no-op for blocking HTTP
def audit(self, state, questions, budget) -> dict: ...  # per-question audit below
def predict(self, states, questions, language, budget, batch_size) -> list: ...
```

`predict` returns one `{"answers": {qid: answer}}` per input state, in order.
choice answer: `{"choice": label, "probabilities": {label: probability, ...}}`.
noul answer: `{"noul": p_true}`. score answer:
`{"score": expected_zero_based_index, "probabilities": {"0": p0, "1": p1, ...}}`.
All probabilities must be finite and in[0,1]. Categorical label keys must match
the complete supplied ontology. A score probability distribution is required;
do not fabricate probabilities from arbitrary confidence or a hard label.

Each audit has `state_tokens`, `head_tokens`, `options`,
`option_texts_shortened`, `unique_encoded_options`, `instruction_shortened`,
`state_shortened`, `special_mask_sanitized`, `complete`.
If a remote API does not expose its actual tokenizer/truncation, use
`complete: false`, conservative flags and an explicit metadata limitation. Do
not assert completeness from a requested token limit alone. The v0.1 schema is
optimized for local Laya; remote-unknown audits require interpreting incomplete
as “unverified”, not evidence that truncation definitely occurred.

The runner persists raw `answer` objects. Adapters must not return private request
text, credential material, or server headers in these objects or metadata.
Keep retries bounded and declare their policy; errors remain in the denominator.
API keys belong in environment variables, never in code, CLI strings, metadata
or committed files. Jev integration awaits the user's model/API details; the
generic interface is implemented, but no Jev adapter or Jev run is claimed.

The benchmark treats the model's `action` as auxiliary output. v0.1 evaluates
labels/probabilities, not a learned escalate/retrieve policy or monetary cost.
