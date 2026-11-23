# URock validation harness

Offline only. Nothing here is imported by `app/`.

URock 2023a (Bernard, Lindberg & Oswald, *Geoscientific Model Development* 16, 5703–5727, [doi:10.5194/gmd-16-5703-2023](https://doi.org/10.5194/gmd-16-5703-2023)) is GPL-3.0. The public code lives in [bbrangeo/urock_processing](https://github.com/bbrangeo/urock_processing) and [UMEP-dev/UMEP](https://github.com/UMEP-dev/UMEP). It needs Java 8 or newer, H2GIS, Jaydebeapi and Numba.

Those packages are not in `backend/requirements.txt` and must not be added for the screening API. `run_check.py` writes `last_run.json` with status, method and limitation. If Java or URock is absent the sidecar says `NOT_RUN` and does not invent a speed.

The intended comparison, when the prerequisite is present, is one north-easterly baseline and one proposed scheme, wind speed sampled at 1.5 m, ranked against the geometric corridor ranking. That ranking stays out of the request path.
