# PIC Test Automation Framework

A Python test-automation framework built around a real instrument: a NanoVNA-H vector network analyzer controlled over USB serial. Measurements flow through a hardware abstraction layer into SQLite, with pass/fail limits in config and statistics in pandas.

## Key Features
* **Hardware Abstraction Layer (HAL):** Every instrument driver implements one abstract interface (`abc`), so the test engine runs unchanged against a physical NanoVNA-H or simulated Keysight and Anritsu VNAs.
* **Production Data Pipeline:** Automated die-level lot sweeping script that pipes parametric measurements directly into a structured SQLite relational database.
* **Statistical Quality Control (SPC):** Features a custom Gage R&R parsing engine written in Pandas to isolate Equipment Variation (Repeatability) from Appraiser/Shift Variation (Reproducibility).
* **Data Sanitization:** Utilizes vectorized Pandas frameworks to calculate line yield statistics before generating shift-end CSV handovers.

## Roadmap
* Calibrated measurements saved as Touchstone files
* Run traceability
* Control charts