Normative Brain TSPO-PET Mapping Across Healthy Aging
Elham Latif
This project explores how TSPO-PET signal varies across healthy adults and whether regional PET signal shows an association with age.
My MSc thesis focused on normative hippocampal volumes from structural MRI. I used FSL/FIRST for subcortical segmentation, corrected volumes for intracranial volume, and compared them across groups.
For this project, I applied a similar idea to molecular imaging: instead of looking at the structural size of the hippocampus, I looked at regional TSPO-PET signal across the brain.
The analysis uses a public OpenNeuro dataset and focuses only on healthy controls. The goal is to demonstrate a complete PET analysis workflow, from image preprocessing and registration to atlas-based ROI extraction and basic normative statistics.
This is an independent analysis of publicly available data and is not affiliated with the original data collection.
Dataset
The data come from OpenNeuro ds007907, a dataset associated with work by Mohammadian, Loggia, and colleagues.
I used the healthy-control participants only. The dataset contains static [¹¹C]PBR28 PET scans together with 3T T1-weighted MRI and participant demographics.
The PET data cover the approximately 60–90 minute post-injection period and are provided in SUV (g/mL). The MRI and PET images are already co-registered in the source dataset.
Raw imaging data are not included in this repository. The download script retrieves only the required healthy-control subjects from OpenNeuro at runtime.
Analysis Pipeline
The workflow consists of four main steps:
1. Download healthy-control data
01_get_hc_subjects.sh
Downloads the required HC participants, including:
•	T1-weighted MRI
•	PET
•	demographic information
Only the required subjects and files are downloaded.
2. MRI/PET preprocessing and registration
02_preprocess_t1_pet.sh
The preprocessing pipeline includes:
•	Brain extraction using FSL BET
•	Linear registration using FLIRT
•	Nonlinear registration to MNI152 2 mm space using FNIRT
•	Application of the resulting transformations to the PET images
PET values remain in their original SUV units throughout the pipeline.
3. Atlas-based ROI extraction
03_extract_roi_values.py
Regional PET signal is extracted using Harvard-Oxford atlas ROIs.
For each participant and region, the script calculates the mean PET SUV and combines the results with available demographic variables such as age and sex.
The output is:
results/roi_suv_values.csv
4. Statistical analysis and visualization
04_analyze_and_plot.py
For each ROI, the analysis includes:
•	Pearson correlation between age and PET SUV
•	Partial correlation between age and PET SUV while controlling for sex
•	Multiple-comparison correction using FDR
•	Regional scatter plots
•	Summary plots of the age associations
The analysis produces CSV results and figures in the results/ directory.

Repository Structure
├── 01_get_hc_subjects.sh
├── 02_preprocess_t1_pet.sh
├── 03_extract_roi_values.py
├── 04_analyze_and_plot.py
├── requirements.txt
├── LICENSE
├── data/
└── results/
Raw imaging files are intentionally excluded from the repository.
Requirements
FSL
The preprocessing scripts require FSL ≥ 6.0, including:
Bet /flirt/ fnirt/ applywarp
If FSL is not installed locally, the pipeline can also be run through Neurodesk Play.
For example:
ml fsl
Python
Install the required Python packages with:
pip install -r requirements.txt
AWS CLI
The first step uses the AWS CLI to retrieve the required files:
pip install awscli
Running the Pipeline
Run the scripts in order:
bash 01_get_hc_subjects.sh
bash 02_preprocess_t1_pet.sh
python 03_extract_roi_values.py
python 04_analyze_and_plot.py
The second step is the most computationally intensive because nonlinear registration with FNIRT can take some time for each participant.
Results
The analysis is intended as a pipeline demonstration rather than a definitive study of age-related TSPO changes.
With the available healthy-control sample, some regions showed nominal associations with age before multiple-comparison correction. After FDR correction across the tested regions, these associations did not remain statistically significant.
This distinction is important because the sample is relatively small and the analysis involves multiple ROIs.
The generated statistical table contains:
•	Pearson correlation coefficient (Pearson_r)
•	Pearson p-value (Pearson_p)
•	Partial correlation controlling for sex (Partial_r_ctrl_sex)
•	Partial p-value (Partial_p)
•	FDR-adjusted p-values
•	Final significance status
Limitations
No reference region
This analysis reports raw PET SUV rather than SUVR.
[¹¹C]PBR28 is a TSPO ligand, and there is no simple brain region that can be assumed to be free of specific TSPO binding. Using an arbitrary reference region would therefore introduce an additional assumption.
A proper SUVR analysis would require a biologically justified and validated reference approach.
No rs6971 genotype correction
TSPO binding with PBR28 is affected by the rs6971 polymorphism, which is associated with different binding affinities.
The participant information available to me from the public dataset did not provide genotype information, so I could not stratify or adjust the analysis for binding-affinity status.
This is an important limitation for interpreting between-subject differences in PBR28 signal.
Small cross-sectional sample
The analysis uses a relatively small healthy-control sample with one scan per participant.
The data are therefore suitable for demonstrating the workflow, but they are not sufficient to establish a general normative trajectory of TSPO binding across aging.
Atlas-based ROIs
The analysis uses Harvard-Oxford atlas regions in standard MNI space rather than subject-specific anatomical segmentation.
This makes the workflow simpler and reproducible, but it may be less anatomically precise than subject-specific ROI definition.
Citation
Mohammadian M, Efthimiou N, Gabriel K, Brusaferri L, Cooper-Hohn J, Kim M, Murphy JP, Alshelh Z, Grmek G, Schnieders JH, Chane CA, Carmichael TG, Yang D, Schubert JJ, Turkheimer FE, Cazuza RA, Grace PM, Catana C, Stufflebeam SM, Edwards RR, Napadow V, Sullivan K, Nahrendorf M, Price TJ, Gilman JM, Loggia ML.
Evidence for a role of skull bone marrow in human chronic pain (as revealed by TSPO PET imaging). Science Translational Medicine.
DOI: 10.1126/scitranslmed.aed8729
Preprint: 10.1101/2025.07.19.25331817
Dataset: OpenNeuro ds007907
DOI: 10.18112/openneuro.ds007907.v1.0.2
License
The code in this repository is released under the MIT License.
The imaging dataset is available through OpenNeuro under CC0. The original imaging data are not redistributed in this repository.

