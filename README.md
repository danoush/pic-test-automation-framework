# High-Volume Manufacturing (HVM) Photonic Integrated Circuit (PIC) Test Framework

A production-grade Python automation architecture designed for high-throughput characterization 
and statistical quality control of electro-optic components (800G/1.6T modulators and photodiodes).

## Key Features
* **Hardware Abstraction Layer (HAL):** Implements an object-oriented decoupled driver architecture using Python Base Classes (`abc`) to seamlessly interchange Keysight and Anritsu Vector Network Analyzers (VNAs) via PyVISA/SCPI.
* **Production Data Pipeline:** Automated die-level lot sweeping script that pipes parametric measurements directly into a structured SQLite relational database.
* **Statistical Quality Control (SPC):** Features a custom Gage R&R parsing engine written in Pandas to isolate Equipment Variation (Repeatability) from Appraiser/Shift Variation (Reproducibility).
* **Data Sanitization:** Utilizes vectorized Pandas frameworks to clear instrumentation clipping errors and calculate line yield statistics before generating shift-end Excel/CSV handovers.
