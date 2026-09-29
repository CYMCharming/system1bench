# Jev hosted evaluation protocol

Frozen before the first formal request on 2026-09-29. Two excluded hand-authored English/Chinese toy requests established authentication and choice/noul/score schema compatibility. They are not benchmark evidence.

- Endpoint: `https://api.typesafe.ai/v1/systemone`; requested and required returned model: `jev-1.13.0`.
- Main matrix: exactly the existing frozen 36 suites, 22,934 requests and 26,450 decisions. Same states, questions, option order and gold scoring rules as the four local checkpoints. No prompt optimization using responses.
- The payload whitelist sends only model, state and questions; gold labels and source metadata never enter the API payload. All payload bytes are transmitted without client truncation. No server tokenizer is exposed, so server-side complete-input verification remains unavailable.
- Up to 12 concurrent workers, at most 15 request starts/s. This is an accuracy collection setting, not controlled sequential service latency. The shared proxy/network/service all contribute to client time. Do not place this time on the local resident-GPU timing frontier.
- Five maximum attempts per request, bounded exponential backoff for 429/529/5xx/transport errors, honoring numeric Retry-After up to 60 seconds. Every attempted call's status, elapsed time and available usage is retained. Authentication/payment/version/schema faults stop further scheduling. Failed benchmark requests remain failures; no favorable retry selection.
- Store append-only request records in manifest order, with request/payload fingerprints, returned answers/model and usage. Resume only with the same contract and runner hash. Never replay already journaled requests. An interrupted process may leave completed-but-not-journaled requests with unknown billing; record such an interruption before resuming.
- Official observed price: USD 0.042 per million input tokens, free output tokens. Accounted usage stops scheduling at USD 10; at most already in-flight requests can overshoot. Usage absent from failed HTTP responses is unknown, so accounted cost is not a billing reconciliation or strict invoice cap. No auto-top-up or account setting changes.
- Preserve raw returned probabilities and Jev confidence. Decode choice as returned argmax, noul at 0.5 and score by probability argmax, with ordinal expected-score errors additionally reported. Calibration analysis uses max class probability consistently; vendor confidence is a separately labeled quantity.
- All intervals/analyses operate on the same state or source clusters as the historical records. Hosted version IDs are pinning evidence, not a weight hash or a guarantee against an unannounced provider change.

Documentation: https://docs.typesafe.ai/api.md and https://docs.typesafe.ai/models.md. Retrieval fingerprints are recorded in the local research source archive. Authentication material is external to the repository and excluded from all artifacts.
