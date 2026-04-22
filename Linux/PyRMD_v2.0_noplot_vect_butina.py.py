#!/usr/bin/env python
# coding: utf-8
#
# PyRMD Studio: A Unified Suite for Next-Generation, AI-Powered Virtual Screening
# Copyright (C) 2021-2026 Benito Natale, Muhammad Waqas, Michele Roggia, Salvatore Di Maro, Sandro Cosconati
# PyRMD Authors: Dr. Giorgio Amendola, Prof. Sandro Cosconati
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
# If you use PyRMD Studio in your work, please cite the following articles:
# PyRMD Studio:
# <XXXX>

# PyRMD:
# <https://pubs.acs.org/doi/full/10.1021/acs.jcim.1c00653>

# PyRMD2Dock:
# <https://pubs.acs.org/doi/10.1021/acs.jcim.3c00647>

# Please check our GitHub page for more information:
# <https://github.com/cosconatilab/PyRMD_Studio>
#------------------------------------------------------------------------------
# ============================================================================
# COMPLETE ORIGINAL CODE OF PyRMD v2.0, (PyRMD_Studio_Engine)
# ============================================================================
# Imports
import os
import re
import time
from pathlib import Path
import subprocess
import sys
import gc
import pickle
import warnings
import multiprocessing as mp
from concurrent.futures import ProcessPoolExecutor, as_completed
from configparser import ConfigParser
import argparse

import numpy as np
import scipy.stats as st
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt

# RDKit Imports
import rdkit
from rdkit import Chem
from rdkit.Chem import AllChem
from rdkit.Chem import PandasTools
from rdkit.Chem import Descriptors
from rdkit.Chem.SaltRemover import SaltRemover
from rdkit.Chem.rdFingerprintGenerator import GetMorganGenerator
from rdkit import rdBase
from rdkit.Chem import rdMHFPFingerprint
from rdkit.ML.Scoring import Scoring
from rdkit.ML.Cluster import Butina
from rdkit.Chem.AtomPairs import Torsions
from rdkit import DataStructs

# Scikit-Learn Imports
import sklearn
from sklearn.model_selection import StratifiedKFold, KFold, RepeatedStratifiedKFold, StratifiedGroupKFold
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import average_precision_score
from sklearn.metrics import precision_recall_curve
from sklearn.metrics import average_precision_score

import statsmodels.stats.api as sms

import openbabel as ob
from openbabel import pybel

import useful_rdkit_utils as uru

matplotlib.use("Agg")
warnings.filterwarnings("ignore")

# ------------------------------------------------------------------------------
# OPTIMIZATION HELPERS
# ------------------------------------------------------------------------------

def get_optimal_processes():
    """Determine optimal number of processes based on system resources"""
    try:
        cpu_count = mp.cpu_count()
        # Leave one core for system processes if more than 2 cores are available
        return max(1, cpu_count - 1) if cpu_count > 2 else cpu_count
    except NotImplementedError:
        return 2

# Set parallel processes
n_processes = get_optimal_processes()
# n_processes = 20 # Hard override if needed
print(f"OPTIMIZATION: Using {n_processes} parallel processes for fingerprint generation")


# ------------------------------------------------------------------------------
# CONFIGURATION
# ------------------------------------------------------------------------------

default_config = """[MODE]

#Indicate if the program is to run in "benchmark" or "screening" mode -- Default: benchmark
mode=benchmark

#Indicate the database file(s) to screen for the screening mode, otherwise leave the entry blank
db_to_screen =

#Specify the output file for the screening mode
screening_output = database_predictions.csv

#Indicate if in screening mode the active compounds should also be converted in a SDF file -- True or False -- Default: False 
sdf_results= False

# For benchmark mode, indicate the file where to output the benchmark results
benchmark_file = benchmark_results.csv

[TRAINING_DATASETS]

# Indicate if one or more ChEMBL databases will be used as training sets -- True or False -- Default: True
use_chembl = True

#Indicate the CHEMBL database(s) file path, otherwise leave the entry blank
chembl_file =

# Set to True if one or more non-CHEMBL databases of active compounds are to be used for training the algorithm, otherwise set to False -- Default: False
use_actives = False

#Indicate the non-CHEMBL active compounds database(s) (SMILES file) path, otherwise leave the entry blank
actives_file =

# Set to True if one or more non-CHEMBL databases(s) of inactive compounds are to be used for training the algorithm, otherwise set to False
use_inactives = False

#Indicate the non-CHEMBL inactive compounds database(s) (SMILES file) file path, otherwise leave the entry blank
inactives_file =


[FINGERPRINTS]

#Fingerprint type - supported formats: rdkit, tt, mhfp, avalon, and ecfp -- Default: mhfp
#For fcfp set fp_type = ecfp and features = True
fp_type = mhfp

# lenght of the fingerprint - typical lenghts are 1024, 2048, and 4096 - longer fingerprints require more memory and are slower to process -- Default: 2048  
nbits = 2048

# Include explicit hydrogens in the fingerprint: True or False -- Default: True
explicit_hydrogens = True

#ecfp/mhfp specific parameters
iterations = 3
chirality = False

#ecfp specific parameters
redundancy = True
features = False

[DECOYS]

#Set to True if external decoys are to be added to the test set for benchmarking the algorithm, otherwise set to False -- Default: False
use_decoys = False

#In case external decoy compounds are to be added to the test set for the benchmark, indicate the decoy database file path, otherwise leave the entry blank
decoys_file =

# Particularly large decoy databases may severely slow down the benchmark process, setting a sample number of decoys to employ can help speed it up -- Default: 1000000
sample_number = 1000000

[CHEMBL_THRESHOLDS]

# Compounds will be considered active if they are reported to have a value of IC50, EC50, Ki, Kd, or potency, inferior to the "activity_threshold" expressed in nM. They will be classified as inactive if their IC50, EC50, Ki, Kd, or potency will be greater than the "inactivity_threshold" expressed in nM, or if their inhibition rate is lower than the "inhibition_threshold" rate -- Default values: activity_threshold = 1001; inactivity_threshold = 39999; inhibition_threshold = 11
activity_threshold = 1001
inactivity_threshold = 39999
inhibition_threshold = 11

[KFOLD_PARAMETERS]

#For statical benchmarking purposes, indicate the number of splits for the benchmark mode -- Default: 5
n_splits = 5

#For statical benchmarking purposes, indicate how many times the benchmarking calculation should be run -- Default: 3
n_repeats = 3

[TRAINING_PARAMETERS]

# Cutoff values that set the percentile of the distance between the compounds in the training set and their projections in the training linear subspace. The resulting maximum projection distance, the epsilon parameter, will be used to classify unknown compounds. Insert a float ranging from 0 to 1 -- Default: 0.95
epsilon_cutoff_actives=0.95
epsilon_cutoff_inactives=0.95

[CLUSTERING]

# Cutoff value (similarity) for performing Butina clustering. Insert a float ranging from 0 to 1 -- Default: 0.70
cutoff = 0.70

[STAT_PARAMETERS]

# F-Score beta value. Beta > 1 gives more weight to TPR, while beta < 1 favors precision. 
beta= 1

# Bedroc alpha value. 
alpha = 20


[FILTER]

#Filter from the SCREENED DATABASE compounds that are not within the specified ranges set below: True or False
filter_properties = False

# If the properties of a compound are not within the specified ranges (specified as integers), the compound will be discarded

molwt_min = 200
logp_min = -5
hdonors_min = 0
haccept_min =0
rotabonds_min =0
heavat_min = 15

molwt_max = 600
logp_max = 5
hdonors_max = 6
haccept_max = 11
rotabonds_max = 9
heavat_max = 51


"""
p = Path("temp_conf_8761.ini")
p.write_text(default_config)


ap = argparse.ArgumentParser()
argv = sys.argv[1:]
if len(argv) == 0:
    p = Path("default_config.ini")
    p.write_text(default_config)
    print(
        "Configuration file path missing, a default_config.ini file has been generated to use as template"
    )
    if os.path.exists("temp_conf_8761.ini"):
        os.remove("temp_conf_8761.ini")
        sys.exit()
ap.add_argument("config", nargs=1, help="configuration file path")
config_file = vars(ap.parse_args())["config"]


def string_or_list(prog_input):
    input_list = prog_input.split()
    if len(input_list) == 1:
        return input_list[0]
    elif len(input_list) > 1:
        return input_list
    else:
        return prog_input


if os.path.exists("temp_conf_8761.ini"):
    config = ConfigParser()
    config.read("temp_conf_8761.ini")
    config.read(config_file)
    default_keys = ["default", "standard", ""]
    os.remove("temp_conf_8761.ini")

# MODE
mode = config.get("MODE", "mode")
verbose = False
score = True
sdf_results = config.getboolean("MODE", "sdf_results")
db_to_screen = string_or_list(config.get("MODE", "db_to_screen"))
benchmark_file = config.get("MODE", "benchmark_file")
gray = False
inactives_similarity = False
inactives_similarity_file = None
screening_output = config.get("MODE", "screening_output")
temporal = False
temporal_file = None

# TRAINING DATASETS
use_chembl = config.getboolean("TRAINING_DATASETS", "use_chembl")
chembl_file = string_or_list(config.get("TRAINING_DATASETS", "chembl_file"))

use_external_actives = config.getboolean("TRAINING_DATASETS", "use_actives")
use_external_inactives = config.getboolean("TRAINING_DATASETS", "use_inactives")
actives_file = string_or_list(config.get("TRAINING_DATASETS", "actives_file"))
inactives_file = string_or_list(config.get("TRAINING_DATASETS", "inactives_file"))

# Fingerprints Parameters
fp_type = config.get("FINGERPRINTS", "fp_type")
explicit_hydrogens = config.getboolean("FINGERPRINTS", "explicit_hydrogens")
iterations = config.getint("FINGERPRINTS", "iterations")
nbits = config.getint("FINGERPRINTS", "nbits")
chirality = config.getboolean("FINGERPRINTS", "chirality")
redundancy = config.getboolean("FINGERPRINTS", "redundancy")
features = config.getboolean("FINGERPRINTS", "features")

# DECOYS
use_external_decoys = config.getboolean("DECOYS", "use_decoys")
decoys_file = string_or_list(config.get("DECOYS", "decoys_file"))
sample_number = config.getint("DECOYS", "sample_number")

# CHEMBL THRESHOLDS
activity_threshold = config.getint("CHEMBL_THRESHOLDS", "activity_threshold")
inactivity_threshold = config.getint("CHEMBL_THRESHOLDS", "inactivity_threshold")
inhibition_threshold = config.getint("CHEMBL_THRESHOLDS", "inhibition_threshold")

# KFOLD PARAMETERS
n_splits = config.getint("KFOLD_PARAMETERS", "n_splits")
n_repeats = config.getint("KFOLD_PARAMETERS", "n_repeats")

# TRAINING PARAMETERS
threshold = config.getfloat("TRAINING_PARAMETERS", "epsilon_cutoff_actives")
threshold_i = config.getfloat("TRAINING_PARAMETERS", "epsilon_cutoff_inactives")
discard_inactives = False
similarity_thres = None

#CLUSTERING
butina_cutoff = 1 - config.getfloat("CLUSTERING", "cutoff")

# STAT PARAMETERS
beta = config.getfloat("STAT_PARAMETERS", "beta")
alpha = config.getfloat("STAT_PARAMETERS", "alpha")


# FILTER
filter_pains = True
filter_properties = config.getboolean("FILTER", "filter_properties")
molwt_min = config.getint("FILTER", "molwt_min")
logp_min = config.getint("FILTER", "logp_min")
hdonors_min = config.getint("FILTER", "hdonors_min")
haccept_min = config.getint("FILTER", "haccept_min")
rotabonds_min = config.getint("FILTER", "rotabonds_min")
heavat_min = config.getint("FILTER", "heavat_min")
molwt_max = config.getint("FILTER", "molwt_max")
logp_max = config.getint("FILTER", "logp_max")
hdonors_max = config.getint("FILTER", "hdonors_max")
haccept_max = config.getint("FILTER", "haccept_max")
rotabonds_max = config.getint("FILTER", "rotabonds_max")
heavat_max = config.getint("FILTER", "heavat_max")


# CONFIG CHECKS
if use_chembl:
    if type(chembl_file) == list:
        for i in chembl_file:
            if not os.path.isfile(i):
                print(f"ERROR: The indicated ChEMBL csv file {i} does not exist")
                sys.exit()
    elif type(chembl_file) == str:
        if not os.path.isfile(chembl_file):
            print(f"ERROR: The indicated ChEMBL csv file {chembl_file} does not exist")
            sys.exit()

if use_external_actives:
    if type(actives_file) == list:
        for i in actives_file:
            if not os.path.isfile(i):
                print(f"ERROR: The indicated active database file {i} does not exist")
                sys.exit()
    elif type(actives_file) == str:
        if not os.path.isfile(actives_file):
            print(
                f"ERROR: The indicated active database file {actives_file} does not exist"
            )
            sys.exit()

if use_external_inactives:
    if type(inactives_file) == list:
        for i in inactives_file:
            if not os.path.isfile(i):
                print(f"ERROR: The indicated inactive database file {i} does not exist")
                sys.exit()
    elif type(inactives_file) == str:
        if not os.path.isfile(inactives_file):
            print(
                f"ERROR: The indicated inactive database file {inactives_file} does not exist"
            )
            sys.exit()

if mode == "screening":
    if type(db_to_screen) == list:
        for i in db_to_screen:
            if not os.path.isfile(i):
                print(
                    f"ERROR: The indicated database to screen file {i} does not exist"
                )
                sys.exit()
    elif type(db_to_screen) == str:
        if not os.path.isfile(db_to_screen):
            print(
                f"ERROR: The indicated database file screen file {db_to_screen} does not exist"
            )
            sys.exit()
    if type(screening_output) != str:
        screening_output = "database_predictions.csv"
    elif len(screening_output) < 2:
        screening_output = "database_predictions.csv"
else:

    if use_external_decoys:
        if type(decoys_file) == list:
            for i in decoys_file:
                if not os.path.isfile(i):
                    print(
                        f"ERROR: The indicated decoys database file {i} does not exist"
                    )
                    sys.exit()
        elif type(decoys_file) == str:
            if not os.path.isfile(decoys_file):
                print(
                    f"ERROR: The indicated decoys database file {decoys_file} does not exist"
                )
                sys.exit()

if fp_type == "mhfp":
    mhfp_encoder = Chem.rdMHFPFingerprint.MHFPEncoder(nbits)
elif fp_type == "avalon":
    from rdkit.Avalon import pyAvalonTools


# # DB preparation functions

def bitjoiner(fp):
    strfp = []
    for i in list(fp):

        strfp.append(str(i))
    return "".join(strfp)


def _calculate_fp_for_molecule_optimized(data_tuple):
    """Optimized worker function for parallel fingerprint calculation"""
    smile, title, index = data_tuple
    rdBase.DisableLog("rdApp.error")

    # Initialize zero fingerprint
    zero_fp = np.zeros(nbits, dtype=np.uint8)
    new_smile = smile
    fp_object = None

    try:
        # First attempt - standard processing
        try:
            mol = pybel.readstring("smi", smile)
            mol.OBMol.StripSalts()
            mol.OBMol.AddHydrogens(False, True)
            mol.OBMol.ConvertDativeBonds()
            new_smile = mol.write().rstrip()
            mol_rd = Chem.MolFromSmiles(new_smile)

            if explicit_hydrogens:
                mol_rd = Chem.RemoveHs(mol_rd)
                mol_rd = Chem.AddHs(mol_rd)

            # Generate fingerprint based on type
            if fp_type == "ecfp":
                fp_object = Chem.AllChem.GetMorganFingerprintAsBitVect(
                    mol_rd,
                    iterations,
                    nBits=nbits,
                    useChirality=chirality,
                    useFeatures=features,
                    includeRedundantEnvironments=redundancy,
                )
                fp1 = np.array([int(x) for x in list(fp_object.ToBitString())], dtype=np.uint8)
            elif fp_type == "rdkit":
                fp_object = Chem.RDKFingerprint(mol_rd, fpSize=nbits)
                fp1 = np.array([int(x) for x in list(fp_object.ToBitString())], dtype=np.uint8)
            elif fp_type == "mhfp":
                fp1 = np.array(
                    mhfp_encoder.EncodeMol(
                        mol_rd, radius=iterations, isomeric=chirality
                    ),
                    dtype=np.uint32,
                )
                fp_object = fp1  # For similarity calculations
            elif fp_type == "tt":
                fp_object = Torsions.GetHashedTopologicalTorsionFingerprint(
                    mol_rd, nbits, includeChirality=chirality
                )
                fp1 = np.array([int(x) for x in list(fp_object)])
            elif fp_type == "avalon":
                fp_object = pyAvalonTools.GetAvalonFP(mol_rd, nBits=nbits)
                fp1 = np.array([int(x) for x in list(fp_object)], dtype=np.uint8)
            else:
                fp1 = zero_fp
                fp_object = zero_fp

        except:
            # Second attempt - alternative processing for problematic molecules
            mol = pybel.readstring("smi", smile)
            mol.OBMol.StripSalts()
            if "[C-]#[N+]" in smile:
                mol.OBMol.AddHydrogens(False, True)
            else:
                mol.OBMol.AddHydrogens(False, False)
                mol.OBMol.ConvertDativeBonds()

            new_smile = mol.write().rstrip()
            mol_rd = Chem.MolFromSmiles(new_smile)

            if explicit_hydrogens:
                mol_rd = Chem.RemoveHs(mol_rd)
                mol_rd = Chem.AddHs(mol_rd)

            # Generate fingerprint based on type (same as above)
            if fp_type == "ecfp":
                fp_object = Chem.AllChem.GetMorganFingerprintAsBitVect(
                    mol_rd,
                    iterations,
                    nBits=nbits,
                    useChirality=chirality,
                    useFeatures=features,
                    includeRedundantEnvironments=redundancy,
                )
                fp1 = np.array([int(x) for x in list(fp_object.ToBitString())], dtype=np.uint8)
            elif fp_type == "rdkit":
                fp_object = Chem.RDKFingerprint(mol_rd, fpSize=nbits)
                fp1 = np.array([int(x) for x in list(fp_object.ToBitString())], dtype=np.uint8)
            elif fp_type == "mhfp":
                fp1 = np.array(
                    mhfp_encoder.EncodeMol(
                        mol_rd, radius=iterations, isomeric=chirality
                    ),
                    dtype=np.uint32,
                )
                fp_object = fp1
            elif fp_type == "tt":
                fp_object = Torsions.GetHashedTopologicalTorsionFingerprint(
                    mol_rd, nbits, includeChirality=chirality
                )
                fp1 = np.array([int(x) for x in list(fp_object)])
            elif fp_type == "avalon":
                fp_object = pyAvalonTools.GetAvalonFP(mol_rd, nBits=nbits)
                fp1 = np.array([int(x) for x in list(fp_object)], dtype=np.uint8)
            else:
                fp1 = zero_fp
                fp_object = zero_fp

    except:
        # Final fallback - use zero fingerprint
        fp1 = zero_fp
        fp_object = zero_fp
        new_smile = smile  # Keep original SMILES

    return (bitjoiner(fp1), fp1, new_smile, fp_object)


def get_fingerprints_ecfp(
    df, string=True, keep_old=False, verbose=verbose, drop_zeros=True, fp_sim=False
):
    """OPTIMIZED fingerprint generation for ultra-large databases (up to 1 billion compounds)
    Features:
    - Parallel processing using all available CPU cores
    - Memory-efficient chunked processing
    - Progress reporting with speed metrics
    - Handles massive datasets through streaming
    """
    start_time = time.time()
    total_mols = len(df)

    # Memory optimization: Use smaller chunk sizes for very large datasets
    if total_mols > 1000000:  # 1M+ compounds
        chunk_size = max(1000, min(10000, total_mols // (n_processes * 10)))
        print(f"OPTIMIZATION: Large dataset detected ({total_mols:,} compounds)")
        print(
            f"OPTIMIZATION: Using chunked processing with {chunk_size} compounds per chunk"
        )
    else:
        chunk_size = min(10000, max(1000, total_mols // n_processes))

    print("Database Preparation: Stripping salts...")
    print(
        "Database Preparation: Calculating tautomeric and protonation states for physiological pH..."
    )

    if fp_type == "ecfp":
        print(
            f"Database Preparation: Converting in {fp_type.upper()} fingerprints, vectors of {nbits} bits with a radius of {iterations}..."
        )
    elif (fp_type == "rdkit") or (fp_type == "avalon"):
        print(
            f"Database Preparation: Converting in {fp_type.upper()} fingerprints, vectors of {nbits} bits..."
        )
    elif fp_type == "tt":
        print(
            f"Database Preparation: Converting in Topological Torsions fingerprints, vectors of {nbits} bits..."
        )
    else:
        print(
            f"Database Preparation: Converting in {fp_type.upper()} fingerprints, with {nbits} permutations and a radius of {iterations}..."
        )

    # Prepare zero fingerprint
    zero_fp = np.zeros(nbits, dtype=np.uint8)
    zero_fp_str = bitjoiner(zero_fp)

    # Initialize result lists
    fp_string_list = [None] * total_mols
    fp_list = [None] * total_mols
    ligprepped_smiles_list = [None] * total_mols
    fps_sim_list = [None] * total_mols if fp_sim else None

    print(
        f"OPTIMIZATION: Processing {total_mols:,} molecules using {n_processes} parallel processes"
    )

    # Process in chunks to handle massive datasets
    processed_count = 0

    for chunk_start in range(0, total_mols, chunk_size):
        chunk_end = min(chunk_start + chunk_size, total_mols)
        chunk_df = df.iloc[chunk_start:chunk_end].copy()

        # Prepare tasks for this chunk
        tasks = [
            (row["Smiles"], row["Title"], chunk_start + idx)
            for idx, (_, row) in enumerate(chunk_df.iterrows())
        ]

        # Process chunk in parallel
        with ProcessPoolExecutor(max_workers=n_processes) as executor:
            futures = {
                executor.submit(_calculate_fp_for_molecule_optimized, task): task[2]
                for task in tasks
            }

            for future in as_completed(futures):
                idx = futures[future]
                try:
                    result = future.result()
                    fp_string_list[idx] = result[0]
                    fp_list[idx] = result[1]
                    ligprepped_smiles_list[idx] = result[2]
                    if fp_sim:
                        fps_sim_list[idx] = result[3]
                except Exception as e:
                    if verbose:
                        print(f"ERROR: Molecule at index {idx} failed: {e}")
                    # Use zero fingerprint for failed molecules
                    fp_string_list[idx] = zero_fp_str
                    fp_list[idx] = zero_fp
                    ligprepped_smiles_list[idx] = tasks[idx - chunk_start][
                        0
                    ]  # Original SMILES
                    if fp_sim:
                        fps_sim_list[idx] = zero_fp

                processed_count += 1

                # Progress reporting
                if (
                    processed_count % max(1, total_mols // 20) == 0
                    or processed_count == total_mols
                ):
                    progress = (processed_count / total_mols) * 100
                    elapsed = time.time() - start_time
                    rate = processed_count / elapsed if elapsed > 0 else 0
                    remaining = (total_mols - processed_count) / rate if rate > 0 else 0
                    print(
                        f"  ... {progress:.1f}% complete ({processed_count:,}/{total_mols:,}) - {rate:.1f} molecules/sec - ETA: {remaining/60:.1f} min"
                    )

        # Memory cleanup after each chunk
        del chunk_df
        gc.collect()

    # Update dataframe with results
    if fp_sim:
        df["fp_sim"] = fps_sim_list
    df["fp_string"] = fp_string_list
    df["fp"] = fp_list
    if keep_old:
        df["Old Smiles"] = df["Smiles"]
    df["Smiles"] = ligprepped_smiles_list

    # Drop zero fingerprints if requested
    if drop_zeros:
        original_count = len(df)
        df = df[df["fp_string"] != zero_fp_str]
        dropped_count = original_count - len(df)
        if dropped_count > 0:
            print(
                f"OPTIMIZATION: Dropped {dropped_count:,} molecules with zero fingerprints"
            )

    df.reset_index(inplace=True, drop=True)
    if not string:
        df = df.drop(["fp_string"], axis=1)

    # Final memory cleanup
    del fp_string_list, fp_list, ligprepped_smiles_list
    if fps_sim_list:
        del fps_sim_list
    gc.collect()

    elapsed_time = time.time() - start_time
    final_rate = total_mols / elapsed_time if elapsed_time > 0 else 0
    print(
        f"Database loaded in {elapsed_time:.2f} seconds ({final_rate:.1f} molecules/sec)"
    )

    return df


######################################


def file_reader(filename):
    """OPTIMIZED file reader for ultra-large datasets (up to 1 billion compounds)
    Features:
    - Chunked reading for memory efficiency
    - Progress reporting for large files
    - Automatic format detection
    - Enhanced error handling
    """

    cols = 2

    def index_namer(name):
        new_name = f"cmp_{str(name)}"
        return new_name

    def is_smile(items):
        if type(items) != list:
            if type(items) == str:
                temp = []
                temp.append(items)
                items = temp
            else:
                items = list(items)
        for i in items:
            try:
                mol = pybel.readstring("smi", i)
                return True
            except:
                pass
        return False

    def column_title_smiles(row):
        for i in row:
            if "smile" in i.lower():
                return i
        return False

    def recognizer_optimized(item):
        """Optimized recognizer for large datasets"""
        nonlocal cols

        if type(item) == pd.core.frame.DataFrame:
            return item

        elif type(item) == str:
            print(f"OPTIMIZATION: Loading dataset from {item}")
            start_time = time.time()

            # Get file size for optimization decisions
            try:
                file_size = os.path.getsize(item)
                file_size_gb = file_size / (1024**3)
                print(f"OPTIMIZATION: File size: {file_size_gb:.2f} GB")

                # Determine if we need chunked reading
                use_chunked_reading = file_size > 100 * 1024 * 1024  # > 100MB

                if use_chunked_reading:
                    # Determine optimal chunk size based on file size
                    if file_size > 5 * 1024**3:  # > 5GB
                        chunksize = 50000
                    elif file_size > 1 * 1024**3:  # > 1GB
                        chunksize = 100000
                    else:
                        chunksize = 100000

                    print(
                        f"OPTIMIZATION: Large file detected, using chunked reading with {chunksize:,} rows per chunk"
                    )
                    return read_large_file_chunked(item, chunksize)

            except OSError:
                print(
                    "OPTIMIZATION: Could not determine file size, using standard reading"
                )

            # Standard reading for smaller files
            try:
                # Try with C engine first (faster and supports low_memory)
                try:
                    df = pd.read_csv(item, sep=",", low_memory=False)
                    cols = len(df.columns)
                except:
                    # Fallback to Python engine (auto-detects separator but doesn't support low_memory)
                    df = pd.read_csv(item, sep=None, engine="python")
                    cols = len(df.columns)
            except Exception as mye:
                if "fields" in str(mye):
                    try:
                        df = pd.read_csv(item, header=None)
                        cols = 1
                    except:
                        df = pd.read_csv(item, header=None, engine="python")
                        cols = 1
                else:
                    print("ERROR: Could not recognize file format")
                    print(f"Error details: {mye}")
                    sys.exit()

            elapsed = time.time() - start_time
            print(
                f"OPTIMIZATION: Loaded {len(df):,} compounds in {elapsed:.2f} seconds"
            )

        return standardize_dataframe(df, cols, item)

    def read_large_file_chunked(filename, chunksize):
        """Read large files in chunks to handle massive datasets"""
        chunks = []
        total_rows = 0
        start_time = time.time()

        # Try different separators and encodings
        separators = [None, ",", "\t", ";", "|"]
        encodings = ["utf-8", "latin-1", "cp1252"]

        chunk_iter = None
        for sep in separators:
            for encoding in encodings:
                try:
                    # Configure parameters based on engine type
                    if sep is None:
                        # Python engine for auto-detection (doesn't support low_memory)
                        chunk_iter = pd.read_csv(
                            filename,
                            chunksize=chunksize,
                            sep=sep,
                            encoding=encoding,
                            dtype=str,  # Read all as strings initially
                            engine="python",
                        )
                    else:
                        # C engine for specific separators (supports low_memory)
                        chunk_iter = pd.read_csv(
                            filename,
                            chunksize=chunksize,
                            sep=sep,
                            encoding=encoding,
                            low_memory=False,
                            dtype=str,  # Read all as strings initially
                            engine="c",
                        )
                    break
                except Exception:
                    continue
            if chunk_iter is not None:
                break

        if chunk_iter is None:
            raise ValueError(
                f"Could not read file {filename} with any separator/encoding combination"
            )

        try:
            for i, chunk in enumerate(chunk_iter):
                # Process chunk
                chunk = standardize_dataframe(
                    chunk, len(chunk.columns), filename, chunk_index=i
                )
                chunks.append(chunk)
                total_rows += len(chunk)

                # Progress reporting
                if (i + 1) % 10 == 0:
                    elapsed = time.time() - start_time
                    rate = total_rows / elapsed if elapsed > 0 else 0
                    print(
                        f"  ... Loaded {total_rows:,} compounds ({rate:.0f} compounds/sec)"
                    )

                # Memory management for very large datasets
                if (
                    total_rows > 10000000 and (i + 1) % 100 == 0
                ):  # Every 100 chunks for 10M+ compounds
                    gc.collect()

        except Exception as e:
            print(f"ERROR: Failed to read chunked file: {e}")
            raise

        # Combine all chunks
        print("OPTIMIZATION: Combining chunks...")
        df = pd.concat(chunks, ignore_index=True)

        elapsed_time = time.time() - start_time
        final_rate = len(df) / elapsed_time if elapsed_time > 0 else 0
        print(
            f"OPTIMIZATION: Loaded {len(df):,} compounds in {elapsed_time:.2f} seconds ({final_rate:.0f} compounds/sec)"
        )

        return df

    def standardize_dataframe(df, cols, filename=None, chunk_index=None):
        """Standardize dataframe column names and structure"""

        # Handle single column case
        if cols == 1:
            df.rename(columns={df.columns[0]: "Smiles"}, inplace=True)

            if not df.empty and not is_smile(df.iloc[0, 0]):
                df = df.iloc[1:].reset_index(drop=True)

            df["Title"] = df.index
            if chunk_index is not None:
                df["Title"] = df["Title"] + (chunk_index * len(df))
            df["Title"] = df["Title"].apply(index_namer)

        else:
            # Handle ChEMBL format
            if "Molecule ChEMBL ID" in (list(df.columns)):
                df.rename(columns={"Molecule ChEMBL ID": "Title"}, inplace=True)

            # Handle SMILES column detection
            elif column_title_smiles(df.columns):
                smiles_col = column_title_smiles(df.columns)
                if smiles_col != "Smiles":
                    df.rename(columns={smiles_col: "Smiles"}, inplace=True)

                # Find Title column
                for i in df.columns:
                    if "title" in i.lower():
                        if i != "Title":
                            df.rename(columns={i: "Title"}, inplace=True)
                        break

                if "Title" not in (list(df.columns)):
                    for i in df.columns:
                        if i != "Smiles":
                            df.rename(columns={i: "Title"}, inplace=True)
                            break

            else:
                # Try to detect SMILES column by content
                if filename and chunk_index is None:  # Only for non-chunked reading
                    df_sample = pd.read_csv(
                        filename, header=None, nrows=100, sep=None, engine="python"
                    )
                    exit_flag = 0
                    for i in range(min(10, len(df_sample))):
                        for j in range(len(df_sample.columns)):
                            if is_smile(df_sample.iloc[i, j]):
                                if j != 0:
                                    df.rename(
                                        columns={
                                            df.columns[j]: "Smiles",
                                            df.columns[0]: "Title",
                                        },
                                        inplace=True,
                                    )
                                else:
                                    df.rename(
                                        columns={
                                            df.columns[0]: "Smiles",
                                            df.columns[1]: "Title",
                                        },
                                        inplace=True,
                                    )
                                exit_flag = 1
                                break
                        if exit_flag == 1:
                            break
                else:
                    # For chunked reading, assume first column is SMILES if not detected
                    if "Smiles" not in df.columns:
                        df.rename(columns={df.columns[0]: "Smiles"}, inplace=True)
                    if "Title" not in df.columns and len(df.columns) > 1:
                        df.rename(columns={df.columns[1]: "Title"}, inplace=True)

        # Ensure Title column exists
        if "Title" not in df.columns:
            df["Title"] = [f"compound_{i}" for i in range(len(df))]

        # Keep only required columns and clean data
        if "Smiles" in df.columns and "Title" in df.columns:
            # df = df[["Smiles", "Title"]].copy()
            df = df.dropna(subset=["Smiles"])
            df = df[df["Smiles"].astype(str).str.strip() != ""]

        return df

    # Main execution
    try:
        if type(filename) == list:
            print(
                "Database preparation: Merging multiple entries in a single dataset..."
            )
            df_list = []
            for i, file in enumerate(filename):
                print(f"Processing file {i+1}/{len(filename)}: {file}")
                df_temp = recognizer_optimized(file)
                df_list.append(df_temp)

            print("OPTIMIZATION: Combining multiple datasets...")
            df = pd.concat(df_list, ignore_index=True)
        else:
            df = recognizer_optimized(filename)

        # Final cleanup
        if len(df) > 100000:  # Only for large datasets
            print("OPTIMIZATION: Performing final cleanup...")
            original_count = len(df)
            df = df.drop_duplicates(subset=["Smiles"], keep="first")
            df = df.reset_index(drop=True)

            duplicates_removed = original_count - len(df)
            if duplicates_removed > 0:
                print(
                    f"OPTIMIZATION: Removed {duplicates_removed:,} duplicate compounds"
                )

        return df

    except UnboundLocalError:
        raise ValueError("Could not recognize file format")
    except Exception as e:
        print(f"ERROR: Failed to load dataset")
        print(f"Error details: {e}")
        print("Please check:")
        print("1. File format (CSV with SMILES column)")
        print("2. File encoding (UTF-8 recommended)")
        print("3. Column separators (comma, tab, semicolon, or pipe)")
        raise


#################################################
def load_decoys(filename, force_sample=True, sample_number=sample_number):
    df = file_reader(filename)

    original_decoy_num = len(df.iloc[:, 0])

    df = df.sort_values(by=["Title"])
    df = df.drop_duplicates(subset="Title", keep="first")
    df = df.dropna(subset=["Smiles"])
    if force_sample == True:
        if len(df["Title"]) > sample_number:
            df = df.sample(n=sample_number)
    df.reset_index(inplace=True)
    df = df.drop("index", axis=1)
    df = get_fingerprints_ecfp(df)
    df = df.drop_duplicates(subset="fp_string", keep="first")
    df.reset_index(inplace=True)
    df = df.drop(["index", "fp_string"], axis=1)

    return original_decoy_num, df


#######################################################


# RETURNS INTER-SIMILARITY BETWEEN DATAFRAMES
def calculate_similarity(df_1, df_2, del_ones=False):
    """Calculate similarity (0–1) between screened compounds and actives, fixing MHFP type issue."""

    df = df_1.copy()  # inactives/screened set
    df2 = df_2.copy()  # actives set
    fp_2 = df2["fp_sim"]
    fp1 = df["fp_sim"]
    
    # print(f"\n[DEBUG] Calculating molecular similarities with fp_type={fp_type}")

    def to_mhfp_list(fp):
        # ensure MHFP vector is a list of python ints for the MHFP encoder
        try:
            arr = np.array(fp, dtype=np.uint32)
            return [int(x) for x in arr] 
        except Exception:
            return []

    def to_bitvect(arr):
        """Convert 0/1 array to RDKit ExplicitBitVect."""
        bitstring = "".join(str(int(x)) for x in arr)
        return DataStructs.CreateFromBitString(bitstring)

    def calc(fp):
        if fp_type == "mhfp":
            fp_list = to_mhfp_list(fp)
            sims = []
            for fp2_item in fp_2:
                fp2_list = to_mhfp_list(fp2_item)
                try:
                    # MHFP encoder returns distance (0..1)
                    dist = mhfp_encoder.Distance(fp_list, fp2_list)
                    sim = 1.0 - dist
                    if sim < 0: sim = 0.0
                    if sim > 1: sim = 1.0
                except Exception as e:
                    # Fallback if MHFP structure is weird
                    try:
                        fp_vec = to_bitvect(fp)
                        fp2_vec = to_bitvect(fp2_item)
                        sim = DataStructs.TanimotoSimilarity(fp_vec, fp2_vec)
                    except:
                        sim = 0.0
                sims.append(sim)
            return pd.Series(sims, index=df2["Title"])
            
        else:
            # Standard Tanimoto for bit vectors
            # This is slow for large sets, might want to optimize with BulkTanimoto
            # but keeping structure for compatibility
            sims = []
            for fp2_item in fp_2:
                try:
                    sims.append(DataStructs.FingerprintSimilarity(fp, fp2_item))
                except:
                    sims.append(0.0)
            return pd.Series(sims, index=df2["Title"])

    matrix = fp1.apply(calc)
    
    df.rename(columns={"Title": "Inactives"}, inplace=True)
    df2.rename(columns={"Title": "Actives"}, inplace=True)
    matrix.index = df["Inactives"]
    matrix.columns = df2["Actives"]

    similarity = matrix.max(axis=1)
    similarity.reset_index(inplace=True, drop=True)

    most_similar = matrix.idxmax(axis=1)
    most_similar.reset_index(inplace=True, drop=True)

    df["similarity"] = similarity
    df["most similar compound"] = most_similar

    if del_ones == True:
        df = df[df["similarity"] != 1]
        df.reset_index(inplace=True)
        df.drop(["similarity", "most similar compound", "index"], axis=1, inplace=True)
    
    # Restore original column name
    df.rename(columns={"Inactives": "Title"}, inplace=True)

    return df


############################################
######## PROPERTIES FILTER ###################


def prop_filter(df_1):

    df = df_1.copy()
    smiles = df["Smiles"]

    def calc(smile):

        m = Chem.MolFromSmiles(smile)

        molwt = int(Descriptors.MolWt(m)) in range(molwt_min, molwt_max + 1)
        logp = int(Descriptors.MolLogP(m)) in range(logp_min, logp_max + 1)
        hdonors = Descriptors.NumHDonors(m) in range(hdonors_min, hdonors_max + 1)
        haccept = Descriptors.NumHAcceptors(m) in range(haccept_min, haccept_max + 1)
        heavat = Descriptors.HeavyAtomCount(m) in range(heavat_min, heavat_max + 1)
        rotabonds = Descriptors.NumRotatableBonds(m) in range(
            rotabonds_min, rotabonds_max + 1
        )

        if (
            molwt
            and logp
            and hdonors
            and haccept
            and haccept
            and heavat
            and rotabonds == True
        ):
            return 0
        else:
            return 1

    df["to_filter"] = smiles.apply(calc)
    df = df[df["to_filter"] == 0]
    df.reset_index(inplace=True, drop=True)
    df.drop(["to_filter"], axis=1, inplace=True)

    return df


######## PAINS FILTER ###################


def pains_filter(df_1):

    from rdkit.Chem import FilterCatalog

    params = FilterCatalog.FilterCatalogParams()
    params.AddCatalog(FilterCatalog.FilterCatalogParams.FilterCatalogs.PAINS_A)
    params.AddCatalog(FilterCatalog.FilterCatalogParams.FilterCatalogs.PAINS_B)
    params.AddCatalog(FilterCatalog.FilterCatalogParams.FilterCatalogs.PAINS_C)
    catalog = FilterCatalog.FilterCatalog(params)

    smiles = df_1["Smiles"]

    def calc(smile):

        m = Chem.MolFromSmiles(smile)
        is_a_pain = catalog.HasMatch(m)

        if is_a_pain:
            return "Yes"
        else:
            return "No"

    df_1["potential_pain"] = smiles.apply(calc)
    # df=df[df['potential_pain'] == 0]
    # df.reset_index(inplace=True,drop=True)
    # df.drop(['potential_pain'], axis = 1, inplace=True)

    return df_1


# This function allows to load a CHEMBL csv, clean it and split it in active set (class 0), inactive set (class 1), and discarded compounds (class 2) for that we have either no data or an activity that is in the so-called grey area
def load_chembl_dataset(file_name, comment=False, gray=False):

    comment_uncertain_keywords = [
        "not determined",
        "no data",
        "nd(insoluble)",
        "not evaluated",
        "dose-dependent effect",
        "uncertain",
        "tde",
        "inconclusive",
        "active-partial",
    ]
    comment_inactive_keywords = ["not active", "inactive"]

    df = file_reader(file_name)

    print(
        f"""\nTraining: Compounds will be considered active if they are reported to have a value of 
          IC50, EC50, Ki, Kd, or potency, inferior to {activity_threshold} nM. 
          They will be classified as inactive if their IC50, EC50, Ki, Kd, or potency will be greater
          than {inactivity_threshold} nM, or if their inhibition rate is lower than {inhibition_threshold}%.
          For duplicate entries, only the most active one will be considered.\n"""
    )

    inactive_types = ["inhibition"]
    active_types = ["ec50", "ic50", "ki", "kd", "potency", "kd apparent"]
    class_list = []

    lower_to_original = {str(column).strip().lower(): column for column in df.columns}
    has_standard_type = "standard type" in lower_to_original
    has_standard_value = "standard value" in lower_to_original

    assays_list = []
    if comment:
        comment_list = []

    if not (has_standard_type and has_standard_value):
        smiles_column = None
        for candidate in ["smiles", "smile", "canonical_smiles"]:
            if candidate in lower_to_original:
                smiles_column = lower_to_original[candidate]
                break

        title_column = None
        for candidate in ["title", "ligand", "name", "molecule", "molecule id", "id", "zinc"]:
            if candidate in lower_to_original:
                title_column = lower_to_original[candidate]
                break

        score_column = None
        for candidate in [
            "lowest_binding_energy",
            "mean_binding_energy",
            "binding_energy",
            "docking_score",
            "score",
            "affinity",
            "vina_score",
            "energy",
        ]:
            if candidate in lower_to_original:
                score_column = lower_to_original[candidate]
                break

        if smiles_column is None or score_column is None:
            missing_fields = []
            if smiles_column is None:
                missing_fields.append("Smiles")
            if score_column is None:
                missing_fields.append("Docking score")
            raise ValueError(
                "Input dataset is missing required columns for both ChEMBL and docking modes: "
                + ", ".join(missing_fields)
            )

        print(
            "Training: ChEMBL assay columns not found; using docking score fallback "
            f"with score column '{score_column}'."
        )

        df = df.dropna(subset=[smiles_column, score_column]).copy()
        df["Smiles"] = df[smiles_column].astype(str).str.strip()

        if title_column is not None:
            df["Title"] = df[title_column].astype(str).str.strip()
            missing_title_mask = df["Title"].isna() | (df["Title"] == "")
            if missing_title_mask.any():
                df.loc[missing_title_mask, "Title"] = [
                    f"cmpd_{idx}" for idx in df.index[missing_title_mask]
                ]
        else:
            df["Title"] = [f"cmpd_{index}" for index in range(len(df))]

        df["Standard Value"] = pd.to_numeric(df[score_column], errors="coerce")
        df = df.dropna(subset=["Smiles", "Standard Value"])
        df["Standard Type"] = "docking_score"
        df["Standard Relation"] = "="
        df["Standard Units"] = "kcal/mol"
        df["Comment"] = "docking_csv"

        score_values = df["Standard Value"].to_numpy(dtype=float)
        lower_cutoff = np.nanpercentile(score_values, 33)
        upper_cutoff = np.nanpercentile(score_values, 67)

        if not np.isfinite(lower_cutoff) or not np.isfinite(upper_cutoff) or lower_cutoff == upper_cutoff:
            median_score = np.nanmedian(score_values)
            lower_cutoff = median_score
            upper_cutoff = median_score

        class_values = np.full(len(df), 2, dtype=int)
        class_values[score_values <= lower_cutoff] = 0
        class_values[score_values >= upper_cutoff] = 1

        if len(df) >= 2 and ((class_values == 0).sum() == 0 or (class_values == 1).sum() == 0):
            ordered_indices = np.argsort(score_values)
            split_index = max(1, len(df) // 2)
            class_values = np.ones(len(df), dtype=int)
            class_values[ordered_indices[:split_index]] = 0

        df["class"] = class_values.tolist()
        assays_list = ["docking_score"]
        if comment:
            comment_list = ["docking_csv"]

        df.reset_index(inplace=True)
        df = df.drop("index", axis=1)
    else:
        df = df.dropna(subset=["Smiles", "Standard Type"])

        df["Standard Value"] = pd.to_numeric(df["Standard Value"], errors="coerce")

        df.reset_index(inplace=True)
        df = df.drop("index", axis=1)

        for i in range(len(df["Standard Type"])):
            c = df.loc[i, "Comment"]

            if type(c) == int:
                c = "number"

            elif type(c) == str:
                if not re.search("\d+", c):
                    c = df.loc[i, "Comment"].lower()
                else:
                    c = "number"
            else:
                c = "number"

            if comment:
                if c not in comment_list:
                    comment_list.append(c)

            t = df.loc[i, "Standard Type"].lower()
            value_raw = df.loc[i, "Standard Value"]
            if pd.isna(value_raw):
                v = np.nan
            else:
                try:
                    v = float(value_raw)
                except (TypeError, ValueError):
                    v = np.nan

            u = df.loc[i, "Standard Units"]
            r = df.loc[i, "Standard Relation"]

            if t not in assays_list:
                assays_list.append(t)

            if c in comment_uncertain_keywords:
                class_list.append(2)
            elif pd.isna(v):
                class_list.append(2)
            elif (
                (t in active_types)
                and (u == "nM")
                and (v < activity_threshold)
                and (r != "'>'")
            ):
                class_list.append(0)
            elif (t in inactive_types) and ((v < inhibition_threshold) and (u == "%")):
                class_list.append(1)
            elif (t in active_types) and (v > inactivity_threshold):
                class_list.append(1)
            elif (t in active_types) and (v < inactivity_threshold):
                class_list.append(2)
            else:
                class_list.append(2)

        df["class"] = class_list

    to_keep = [
        "Title",
        "Smiles",
        "Standard Value",
        "Standard Type",
        "Standard Relation",
        "Standard Units",
        "class",
        "Comment",
    ]
    for i in dict(df).keys():
        if i not in to_keep:
            df = df.drop(i, axis=1)

    df = df.sort_values(by=["Title", "class", "Standard Value"])
    df = df.drop_duplicates(subset="Title", keep="first")

    df = df.dropna(subset=["Smiles"])
    df.reset_index(inplace=True)
    df = df.drop("index", axis=1)

    df = get_fingerprints_ecfp(df, fp_sim=True)
    if gray:
        df_gray = df[df["class"] == 2]
        df_gray.reset_index(inplace=True, drop=True)

    df = df[df["class"] != 2]
    df.reset_index(inplace=True)
    df = df.drop("index", axis=1)

    # df = df.sort_values(by=['class'])
    # df = df.drop_duplicates(subset = 'fp_string', keep = 'first')

    # df.reset_index(inplace = True)
    # df = df.drop(['index','fp_string'], axis = 1)
    print("Database preparation: Removing duplicate entries...")

    if comment:
        return df, assays_list, comment_list
    elif gray:
        return df, df_gray
    else:
        return df


###########################################
# # Algorithm Functions
###########################################


def scaler_light(X_train, y_train):

    training_a = X_train[y_train == 0]
    training_i = X_train[y_train == 1]

    scaler_a = StandardScaler().fit(training_a)
    scaler_i = StandardScaler().fit(training_i)

    training_a = scaler_a.transform(training_a)
    training_i = scaler_i.transform(training_i)

    #    # Original
    #    active_columns_del = []
    #    for i in range(training_a.shape[1]):
    #        if training_a[:, i].std() == 0.0:
    #            active_columns_del.append(i)
    #
    #    inactive_columns_del = []
    #    for i in range(training_i.shape[1]):
    #        if training_i[:,i].std()==0.0:
    #            inactive_columns_del.append(i)

    # Vectorization
    active_columns_del = np.where(training_a.std(axis=0) == 0.0)[0].tolist()
    inactive_columns_del = np.where(training_i.std(axis=0) == 0.0)[0].tolist()

    training_a = np.delete(training_a, active_columns_del, axis=1)
    training_i = np.delete(training_i, inactive_columns_del, axis=1)

    return training_a, training_i


#########################################################


def scaler_external(X_train, y_train, ligands):

    training_a = X_train[y_train == 0]
    training_i = X_train[y_train == 1]

    scaler_a = StandardScaler().fit(training_a)
    scaler_i = StandardScaler().fit(training_i)

    training_a = scaler_a.transform(training_a)
    training_i = scaler_i.transform(training_i)
    ligands_activescaled = scaler_a.transform(ligands)
    ligands_inactivescaled = scaler_i.transform(ligands)

    #    # Original code
    #    active_columns_del = []
    #    for i in range(training_a.shape[1]):
    #        if training_a[:, i].std() == 0.0:
    #            active_columns_del.append(i)
    #
    #    inactive_columns_del = []
    #    for i in range(training_i.shape[1]):
    #        if training_i[:, i].std() == 0.0:
    #            inactive_columns_del.append(i)

    # Vectorization
    active_columns_del = np.where(training_a.std(axis=0) == 0.0)[0].tolist()
    inactive_columns_del = np.where(training_i.std(axis=0) == 0.0)[0].tolist()

    training_a = np.delete(training_a, active_columns_del, axis=1)
    training_i = np.delete(training_i, inactive_columns_del, axis=1)

    ligands_activescaled = np.delete(ligands_activescaled, active_columns_del, axis=1)
    ligands_inactivescaled = np.delete(
        ligands_inactivescaled, inactive_columns_del, axis=1
    )

    return ligands_activescaled, ligands_inactivescaled


#########################################


def scaler(X_train, X_test, y_train, y_test):

    training_a = X_train[y_train == 0]
    training_i = X_train[y_train == 1]
    testset_a = X_test[y_test == 0]
    testset_i = X_test[y_test == 1]

    scaler_a = StandardScaler().fit(training_a)
    scaler_i = StandardScaler().fit(training_i)

    training_a = scaler_a.transform(training_a)
    training_i = scaler_i.transform(training_i)

    testset_a_activescaled = scaler_a.transform(testset_a)
    testset_a_inactivescaled = scaler_i.transform(testset_a)

    testset_i_activescaled = scaler_a.transform(testset_i)
    testset_i_inactivescaled = scaler_i.transform(testset_i)

    #    # Original
    #    active_columns_del = []
    #    for i in range(training_a.shape[1]):
    #        if training_a[:, i].std() == 0.0:
    #            active_columns_del.append(i)
    #
    #    inactive_columns_del = []
    #    for i in range(training_i.shape[1]):
    #        if training_i[:, i].std() == 0.0:
    #            inactive_columns_del.append(i)

    # Vectorization
    active_columns_del = np.where(training_a.std(axis=0) == 0.0)[0].tolist()
    inactive_columns_del = np.where(training_i.std(axis=0) == 0.0)[0].tolist()

    training_a = np.delete(training_a, active_columns_del, axis=1)
    training_i = np.delete(training_i, inactive_columns_del, axis=1)

    testset_a_activescaled = np.delete(
        testset_a_activescaled, active_columns_del, axis=1
    )
    testset_a_inactivescaled = np.delete(
        testset_a_inactivescaled, inactive_columns_del, axis=1
    )

    testset_i_activescaled = np.delete(
        testset_i_activescaled, active_columns_del, axis=1
    )
    testset_i_inactivescaled = np.delete(
        testset_i_inactivescaled, inactive_columns_del, axis=1
    )

    return (
        training_a,
        testset_a_activescaled,
        testset_a_inactivescaled,
        training_i,
        testset_i_activescaled,
        testset_i_inactivescaled,
    )


#########################################
######### Core RMD Algorithm ############
#########################################

# Original proj_vect() function:
# def proj_vect(mu, num_eig, p, vv):
#    mu_proj = np.zeros(p)
#    for counter in range(num_eig):
#        vect_prod = float(np.vdot(vv[:,counter], mu))
#        mu_proj = mu_proj +vect_prod * vv[:,counter]
#    return np.array([float(i) for i in mu_proj])


# Vectorization of the previous function:
def proj_vect(mu, num_eig, p, vv):
    # Compute dot products for all eigenvectors at once
    # print(vv[:, :num_eig].shape, mu.shape)
    vect_prods = np.dot(vv[:, :num_eig].T, mu)
    # Multiply each eigenvector by its corresponding dot product and sum them up
    mu_proj = np.dot(vv[:, :num_eig], vect_prods)

    return mu_proj


class RMDClassifier(object):

    def __init__(self, threshold=threshold, threshold_i=threshold_i):
        self.threshold = threshold
        self.epsilon = None
        self.vv = None
        self.num_eig = None
        self.p = None
        self.threshold_i = threshold_i
        self.epsilon_i = None
        self.vv_i = None
        self.num_eig_i = None
        self.p_i = None

    def fit(self, training_set):
        n, p = training_set.shape
        self.p = p
        covar = np.dot(training_set.T, training_set) / n
        eigen_values, eigen_vectors = np.linalg.eigh(covar)
        counter = eigen_values.argsort()
        counter = counter[::-1]
        eigen_values = eigen_values[counter]
        eigen_vectors = eigen_vectors[:, counter]
        MP_bound = (1 + np.sqrt(p / n)) ** 2
        num_eig = eigen_values[eigen_values > MP_bound].shape[0]
        vv = eigen_vectors[:, :num_eig]
        self.num_eig, self.vv = num_eig, vv

        #        # Original
        #        euc_distance = []
        #        for mol_vec_counter in range(n):
        #            mu = training_set[mol_vec_counter,:]
        #            mu_proj = proj_vect(mu, num_eig, p, vv)
        #            euc_distance.append(np.linalg.norm(mu-mu_proj))

        # Vectorization
        mu_proj = np.dot(training_set, vv) @ vv.T
        euc_distance = np.linalg.norm(training_set - mu_proj, axis=1)

        euc_distance.sort()
        # euc_distance = np.array(euc_distance)
        cutoff_counter = int(self.threshold * len(euc_distance))
        epsilon = euc_distance[cutoff_counter]
        self.epsilon = epsilon

    def fit_i(self, training_set):

        n, p = training_set.shape
        self.p_i = p
        covar = np.dot(training_set.T, training_set) / n
        eigen_values, eigen_vectors = np.linalg.eigh(covar)
        counter = eigen_values.argsort()
        counter = counter[::-1]
        eigen_values = eigen_values[counter]
        eigen_vectors = eigen_vectors[:, counter]
        MP_bound = (1 + np.sqrt(p / n)) ** 2
        num_eig = eigen_values[eigen_values > MP_bound].shape[0]
        vv = eigen_vectors[:, :num_eig]
        self.num_eig_i, self.vv_i = num_eig, vv

        #        # Original
        #        euc_distance = []
        #        for mol_vec_counter in range(n):
        #            mu = training_set[mol_vec_counter,:]
        #            mu_proj = proj_vect(mu, num_eig, p, vv)
        #            euc_distance.append(np.linalg.norm(mu-mu_proj))

        # Vectorization
        mu_proj = np.dot(training_set, vv) @ vv.T
        euc_distance = np.linalg.norm(training_set - mu_proj, axis=1)

        euc_distance.sort()
        # euc_distance = np.array(euc_distance)
        cutoff_counter = int(self.threshold_i * len(euc_distance))
        epsilon = euc_distance[cutoff_counter]
        self.epsilon_i = epsilon

    def predict(self, unknown_set, unknown_set_i, score=False):
        # Vectorization
        mu_proj = np.dot(unknown_set, self.vv) @ self.vv.T
        mu_proj_i = np.dot(unknown_set_i, self.vv_i) @ self.vv_i.T

        unknown_set_euc_distance = np.linalg.norm(unknown_set - mu_proj, axis=1)
        unknown_set_euc_distance_i = np.linalg.norm(unknown_set_i - mu_proj_i, axis=1)

        predictions = []
        if not score:
            x = unknown_set_euc_distance
            y = unknown_set_euc_distance_i

            predictions = np.where(
                x >= self.epsilon,
                0,
                np.where(
                    y > self.epsilon_i,
                    1,
                    np.where((x - self.epsilon) < (y - self.epsilon_i), 1, 0),
                ),
            )

            return predictions

        else:
            x = unknown_set_euc_distance
            y = unknown_set_euc_distance_i

            predictions = np.where(
                x >= self.epsilon,
                0,
                np.where(
                    y > self.epsilon_i,
                    1,
                    np.where((x - self.epsilon) < (y - self.epsilon_i), 1, 0),
                ),
            )

            RMD_score = np.where(
                x >= self.epsilon,
                x - self.epsilon,
                np.where(
                    y > self.epsilon_i,
                    x - self.epsilon,
                    (x - self.epsilon) - (y - self.epsilon_i),
                ),
            )

            RMD_score = np.nan_to_num(RMD_score, nan=0)

            df = pd.DataFrame({"predictions": predictions, "RMD_score": RMD_score})

            return df


# # Algorithm benchmarking functions


# Let's calculate the ROC metrics and Precision-Recall Curve!
def get_auc(
    actives_preds,
    inactives_preds,
    rep,
    fold,
    plot_roc=False,
    plot_prc=False,
    roc_plot_path="ROC_curve.png",
    prc_plot_path="PRC_curve.png",
):
    actives_preds["real binder"] = 1
    inactives_preds["real binder"] = 0
    auc_df = pd.concat([actives_preds, inactives_preds])
    auc_df = auc_df.sort_values(by=["RMD_score"])
    auc_df.reset_index(inplace=True)
    auc_df = auc_df.drop("index", axis=1)

    y_true = auc_df["real binder"]
    y_scores = auc_df["RMD_score"] * (-1)
    # sklearn.metrics.roc_auc_score(y_true, y_scores)

    # Replace NaN values with 0
    y_true = y_true.fillna(0)
    y_scores = y_scores.fillna(0)

    ##############   ROC   ############################
    fpr, tpr, _ = sklearn.metrics.roc_curve(y_true, y_scores, drop_intermediate=True)
    # fpr,tpr = get_tpr_fpr(auc_df)
    roc_auc = sklearn.metrics.auc(fpr, tpr)

    if plot_roc == True:
        plt.figure()
        lw = 2
        plt.plot(
            fpr,
            tpr,
            color="darkorange",
            lw=lw,
            label="Area Under the Curve = %0.2f)" % roc_auc,
        )
        plt.plot([0, 1], [0, 1], color="navy", lw=lw, linestyle="--")
        plt.xlim([0.0, 1.0])
        plt.ylim([0.0, 1.05])
        plt.xlabel("False Positive Rate")
        plt.ylabel("True Positive Rate")
        # plt.title(f'Rep {rep} Fold {fold} ROC')
        plt.title(f"ROC curve")
        plt.legend(loc="lower right")
        plt.savefig(roc_plot_path, dpi=300)
        # plt.savefig(f'Rep_{rep}_Fold_{fold}_ROC.png', dpi=300)
        # print(fpr)

    ###################   PRC    #########################
    # ap=average_precision_score(y_true, y_scores)
    # print(f'AP = {ap}')
    precision, recall, thresholds = precision_recall_curve(y_true, y_scores)
    prc_auc = sklearn.metrics.auc(recall, precision)
    # print(f'PRC AUC = {prc_auc}')

    if plot_prc == True:
        plt.figure()
        lw = 2
        plt.plot(
            recall,
            precision,
            color="orangered",
            lw=lw,
            label="Area Under the Curve = %0.2f)" % prc_auc,
        )
        # no_skill = len(y_true[y_true==1]) / len(y_true)
        # plt.plot([0, 1], [no_skill, no_skill], color='navy', lw=lw, linestyle='--')
        plt.xlim([0.0, 1.0])
        plt.ylim(top=1.0)
        plt.title(f"PRC curve")
        plt.xlabel("Recall")
        plt.ylabel("Precision")
        plt.legend(loc="lower left")
        plt.savefig(prc_plot_path, dpi=300)

    return roc_auc, prc_auc


###################################################


def get_precision_stats(actives_preds, inactives_preds, beta=beta):

    actives_preds["real binder"] = 1
    inactives_preds["real binder"] = 0
    df = pd.concat([actives_preds, inactives_preds])
    df = df.sort_values(by=["RMD_score"])
    df.reset_index(inplace=True, drop=True)

    y_true = df["real binder"]
    y_pred = df["predictions"]

    number_of_tp = len(actives_preds[actives_preds["predictions"] == 1])
    number_of_fp = len(inactives_preds[inactives_preds["predictions"] == 1])
    try:
        precision = number_of_tp / (number_of_tp + number_of_fp)
    except:
        precision = 0
    f_score = sklearn.metrics.fbeta_score(y_true, y_pred, beta=beta)

    #### BEDROC

    scores = np.array(df.drop("predictions", axis=1))
    bedroc = Scoring.CalcBEDROC(scores, 1, alpha)

    return precision, f_score, bedroc


######################################################
def get_confidence_interval(a):

    lower, upper = st.t.interval(0.95, len(a) - 1, loc=np.mean(a), scale=st.sem(a))
    # print(sms.DescrStatsW(a).tconfint_mean())
    # print(st.norm.interval(0.95, loc=np.mean(a), scale=st.sem(a)))
    estimate = (lower + upper) / 2
    margin = upper - estimate
    print(f"~~ {estimate:.3f} ± {margin:.3f}")
    return estimate, margin


#################################################


def get_fold_number(index):

    # index=((rep-1)*10)+fold-1
    if len(str(index)) == 2:
        rep = int(str(index)[0]) + 1
        fold = int(str(index)[1]) + 1
    else:
        rep = 1
        fold = int(str(index)[0]) + 1
    # print(f'Rep {rep} Fold {fold}')
    return rep, fold


# # EXECUTION


def list_2_string(prog_input):
    if type(prog_input) == list:
        return (" ").join(prog_input)
    else:
        return prog_input


# Databases loading
print(
    """
*********************************************************************************************
* PyRMD Studio: A Unified Suite for Next-Generation, AI-Powered Virtual Screening           *
* Copyright (C) 2021-2026 Benito Natale, Muhammad Waqas, Michele Roggia, Salvatore Di Maro, *
* Sandro Cosconati                                                                          *
* PyRMD Authors: Dr. Giorgio Amendola, Prof. Sandro Cosconati                               *
* This program is free software: you can redistribute it and/or modify                      *
* it under the terms of the GNU Affero General Public License as published                  *
* by the Free Software Foundation, either version 3 of the License, or                      *
* (at your option) any later version.                                                       *
* This program is distributed in the hope that it will be useful,                           *
* but WITHOUT ANY WARRANTY; without even the implied warranty of                            *
* MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the                             *
* GNU Affero General Public License for more details.                                       *
* You should have received a copy of the GNU Affero General Public License                  *
* along with this program.  If not, see <https://www.gnu.org/licenses/>.                    *
* If you use PyRMD Studio in your work, please cite the following articles:                 *
* PyRMD Studio: <XXXX>                                                                      *
* PyRMD: <https://pubs.acs.org/doi/full/10.1021/acs.jcim.1c00653>                           *
* PyRMD2Dock: <https://pubs.acs.org/doi/10.1021/acs.jcim.3c00647>                           *
* Please check our GitHub page for more information:                                        *
* <https://github.com/cosconatilab/PyRMD_Studio>                                            *
*********************************************************************************************
"""
)
print(
    """                                                                                
                                                                                
                                                                                
                                                                                
                                       (((                                      
                                      (((((                                     
                                    ((((((((                                    
                                   (((((((((                                    
                                 ((((((((((   %%                                
                                ((((((((((   %%%%                               
                              ####((((((   %%%%%%%%                             
                            (#########(    %%%%%%%%%                            
                           ##########       %%%%%%%%%%                          
                         ###########         %%%%%%#####                        
                        %%%#######             ##########                       
                      %%%%%%%%%##               ###########                     
                     (%%%%%%%%%                   ##########                    
                   (((%%%%%%%(                     #########((                  
                  ((((#%%%%%                         ##((((((((                 
                 (((((##%%%                           %(((((((((                
                 (((#########                       %%%%((((((((                
                  (##########%%%%               %%%%%%%%(((((((                 
                    #######%%%%%%%%%%&     #####%%%%%%%((((((                   
                        #%%%%%%%%     (###########%%%%(((                       
                                 ,((((((###########%                            
                                 (((((((((#####/                                
                                       (((                                      
                                                                                
                                                                                
                                                                                
        &&&&&&&&&&            &&&&&&&&&&   (&&&       &&&&   &&&%&&&&&&         
        &&&&  &&&& &&&   &&&  &&&&  /&&&   &&&&&.    &&&&&   &&&#   &&&&        
        %&&&%&&&%  &%&   &&&  &&%&&&%&&    &%&&&%   %&&&%&   &&&(    &&&%       
        &&&&       &&&   &&&  &&&&  &&&&   &&& &&& &&& &&&   &&&#    &&&        
        &&&&       &&&&&&&&&, &&&&   &&&&  &&&  &&&&&  &&&&  &&&%&&&&&&         
                          &&&                                                   
                    &&&&&&&&                                                    
 
        &&&&&&&   &&&&&&&&&   &&&    &&&  &&&&&     &&&&&&&&  &&&&&&&&         
        &&&          &&&      &&&    &&&  &&&  &&&    &&&&    &&    &&          
        &&&&&&&      &&&      &&&    &&&  &&&   &&&   &&&&    &&    &&          
             &&&     &&&      &&&    &&&  &&&  &&&    &&&&    &&    &&          
        &&&&&&&      &&&      &&&&&&&&&&  &&&&&     &&&&&&&&  &&&&&&&&         
 
 
            +----------------------------------------------------------------------------------------------+
            |       PyRMD_Studio: A Unified Suite for Next-Generation, AI-Powered Virtual Screening        |
            |                                                                                              |
            |                                   ~~~~ Cosconati Lab ~~~~                                    |                                               |
            +----------------------------------------------------------------------------------------------+
\n"""
)

if mode == "benchmark":
    print("//////// BENCHMARK MODE \\\\\\\\\\\\\\\\ ")
elif mode == ("screening"):
    print("//////// SCREENING MODE \\\\\\\\\\\\\\\\ ")

else:
    print("Please indicate a valid mode in the configuration file")
    sys.exit()


print("\n----BUILDING TRAINING DATASET----\n")

if use_chembl:
    print(f"Training: Loading the ChEMBL dataset(s): {list_2_string(chembl_file)}")
    if gray:
        df_training, df_gray = load_chembl_dataset(chembl_file, gray=True)
        df_gray = df_gray.drop(["fp", "fp_sim", "fp_string"], axis=1)
        df_gray.to_csv(path_or_buf="chembl_discarded.csv", index=False)
        print(
            "Training: Discarded compounds from the ChEMBL database have been written to chembl_discarded.csv"
        )
    else:
        df_training = load_chembl_dataset(chembl_file)
    if use_external_actives:
        print(
            f"Training: Loading the active compounds dataset(s): {list_2_string(actives_file)}"
        )
        df_actives = file_reader(actives_file)
        df_actives = get_fingerprints_ecfp(df_actives, fp_sim=True)
        df_actives["class"] = 0
        df_training = pd.concat([df_training, df_actives], ignore_index=True)
    if use_external_inactives:
        print(
            f"Training: Loading the inactive compounds dataset(s): {list_2_string(inactives_file)}"
        )
        df_inactives = file_reader(inactives_file)
        df_inactives = get_fingerprints_ecfp(df_inactives, fp_sim=True)
        df_inactives["class"] = 1
        df_training = pd.concat([df_training, df_inactives], ignore_index=True)
    df_training = df_training.sort_values(by=["class"])
    df_training = df_training.drop_duplicates(subset="fp_string", keep="first")
    df_training.reset_index(inplace=True)
    df_training = df_training.drop(["index", "fp_string"], axis=1)

elif use_external_actives:
    print(
        f"Training: Loading the active compounds dataset(s): {list_2_string(actives_file)}"
    )
    if use_external_inactives:
        print(
            f"Training: Loading the inactive compounds dataset(s): {list_2_string(inactives_file)}"
        )
        df_actives = file_reader(actives_file)
        df_inactives = file_reader(inactives_file)
        df_inactives["class"] = 1
        df_actives["class"] = 0
        df_training = pd.concat([df_inactives, df_actives], ignore_index=True)
        df_training = get_fingerprints_ecfp(df_training, fp_sim=True)
        df_training = df_training.sort_values(by=["class"])
        df_training = df_training.drop_duplicates(subset="fp_string", keep="first")
        df_training.reset_index(inplace=True)
        df_training = df_training.drop(["index", "fp_string"], axis=1)

    else:
        raise ValueError(
            "If you are not using a CHEMBL database, both an active compounds database and an inactive compounds database are required"
        )
else:
    raise ValueError(
        "If you are not using a CHEMBL database, both an active compounds database and an inactive compounds database are required"
    )


# Writing a clean and human-readable copy of the training dataset
df_to_write = df_training.copy()
if "Comment" in list(df_to_write.columns):
    df_to_write = df_to_write.drop(["fp", "Comment", "fp_sim"], axis=1)
else:
    df_to_write = df_to_write.drop(["fp", "fp_sim"], axis=1)

df_to_write["class"] = (
    df_to_write["class"]
    .map({0: "Active", 1: "Inactive"})
    .fillna(df_to_write["class"].astype(str))
)
inactives_num = len(df_to_write[df_to_write["class"] == "Inactive"])
actives_num = len(df_to_write[df_to_write["class"] == "Active"])
print(
    f"Training: The training dataset consists of {actives_num} active compounds and {inactives_num} inactive compounds"
)
print(
    "Training: The training dataset has been written to the file clean_training_db.csv"
)
df_to_write.to_csv(path_or_buf="clean_training_db.csv", index=False)
print("Training dataset preparation is complete!\n")

decoy_num = 0
original_decoy_num = 0

# LOADING DECOYS
if (use_external_decoys == True) and (mode == "benchmark"):
    print("\n----BUILDING DECOY DATASET----\n")

    print(
        f"Decoys: Loading the decoy compounds dataset(s): {list_2_string(decoys_file)}"
    )

    print(
        "Decoys: Decoy compounds will only be used for benchmarking purposes, they will not be used to train the algorithm"
    )
    original_decoy_num, df_decoys = load_decoys(decoys_file, force_sample=True)
    decoy_num = len(df_decoys.iloc[:, 0])
    print(
        f"Decoys: The decoy dataset consists of {original_decoy_num} compounds. Duplicate compounds will be discarded"
    )
    print("Decoys dataset preparation is complete!\n")


######SIMILARITY CALCULATIONS
df_actives = df_training[df_training["class"] == 0]
df_actives.reset_index(inplace=True, drop=True)

if inactives_similarity:
    print(
        "Calculating pairwise similarity between the inactives data set and the actives"
    )
    df_inactives = df_training[df_training["class"] == 1]
    df_inactives.reset_index(inplace=True, drop=True)
    df_inactives = calculate_similarity(df_inactives, df_actives)
    df_inactives = df_inactives.drop(["fp", "fp_sim"], axis=1)
    df_inactives.to_csv(path_or_buf=inactives_similarity_file, index=False)
    print(
        f"The inactives similarity to the actives has been written to {inactives_similarity_file}"
    )


print("Preparing for calculations...\n")


# CHECKPOINT 1: Save the training set X and labels y to disk
if use_external_decoys and mode == "benchmark":
    checkpoint_files = {
        "X": "temp_X_training.pkl",
        "y": "temp_y_training.pkl",
        "cluster_list": "temp_cluster_list_training.pkl",
        "fingerprints_decoys": "temp_fingerprints_decoys_training.pkl",
    }
else:
    checkpoint_files = {
        "X": "temp_X_training.pkl",
        "y": "temp_y_training.pkl",
        "cluster_list": "temp_cluster_list_training.pkl",
    }

# Load the training set and labels from disk
checkpoint_loaded = False
if all(os.path.exists(file) for file in checkpoint_files.values()):
    data = {}
    for key, file in checkpoint_files.items():
        with open(file, "rb") as f:
            data[key] = pickle.load(f)

    cached_X = data["X"]
    cached_y = data["y"]
    cached_cluster_list = data["cluster_list"]

    cache_is_compatible = True
    try:
        cached_X_array = np.asarray(cached_X)
        if cached_X_array.ndim != 2:
            cache_is_compatible = False
        elif cached_X_array.shape[1] != int(nbits):
            cache_is_compatible = False
        elif len(cached_y) != cached_X_array.shape[0]:
            cache_is_compatible = False
        elif len(cached_cluster_list) != cached_X_array.shape[0]:
            cache_is_compatible = False

        if use_external_decoys and mode == "benchmark":
            cached_decoys = np.asarray(data.get("fingerprints_decoys", []))
            if cached_decoys.size > 0 and (cached_decoys.ndim != 2 or cached_decoys.shape[1] != int(nbits)):
                cache_is_compatible = False
    except Exception:
        cache_is_compatible = False

    if cache_is_compatible:
        X = cached_X
        y = cached_y
        cluster_list = cached_cluster_list

        if use_external_decoys and mode == "benchmark":
            fingerprints_decoys = data["fingerprints_decoys"]

        checkpoint_loaded = True

        print("Loaded training set and labels from disk.\n")
        print(f"Clusters found: {len(cluster_list) + 1}")
    else:
        print(
            "Checkpoint cache is incompatible with current settings "
            f"(expected nbits={nbits}). Rebuilding training checkpoint..."
        )
        for file in checkpoint_files.values():
            try:
                if os.path.exists(file):
                    os.remove(file)
            except Exception:
                pass

if not checkpoint_loaded:
################ CLUSTERING ################
    # Use the CORRECTED clustering logic
    
    print(f"Clustering: Preparing molecules for clustering using {fp_type.upper()} fingerprints...")
    
    # 1. Prepare molecules
    df_training_copy = df_training[["Smiles", "fp", "class"]].copy()
    df_training_copy["mol"] = df_training_copy["Smiles"].apply(Chem.MolFromSmiles)
    
    # 2. Generate Fingerprints list for Clustering
    fp_list_clustering = []
    
    # --- GENERATION BLOCK ---
    if fp_type == 'mhfp':
        # MHFP: Generate list of MinHash arrays (list of lists/arrays)
        # Note: mhfp_encoder is already initialized globally
        fp_list_clustering = [mhfp_encoder.EncodeMol(m, radius=iterations, isomeric=chirality) for m in df_training_copy["mol"]]
        
    elif fp_type == 'ecfp':
        # ECFP: Generate ExplicitBitVects
        generator = GetMorganGenerator(radius=iterations, fpSize=nbits)
        fp_list_clustering = [generator.GetFingerprint(m) for m in df_training_copy["mol"]]
        
    elif fp_type == 'rdkit':
        # RDKit: Generate ExplicitBitVects
        fp_list_clustering = [Chem.RDKFingerprint(m, fpSize=nbits) for m in df_training_copy["mol"]]
        
    elif fp_type == 'tt':
        # Topological Torsion: Generate ExplicitBitVects
        fp_list_clustering = [Torsions.GetHashedTopologicalTorsionFingerprint(m, nBits=nbits) for m in df_training_copy["mol"]]
        
    elif fp_type == 'avalon':
        # Avalon: Generate ExplicitBitVects
        fp_list_clustering = [pyAvalonTools.GetAvalonFP(m, nBits=nbits) for m in df_training_copy["mol"]]
        
    else:
        # Default fallback to Morgan
        generator = GetMorganGenerator(radius=iterations, fpSize=nbits)
        fp_list_clustering = [generator.GetFingerprint(m) for m in df_training_copy["mol"]]

    # 3. Calculate Distance Matrix (Lower Triangular)
    # This logic is now UNIVERSAL: we explicitly calculate distances before clustering
    print(f"Clustering: Calculating distance matrix for {len(fp_list_clustering)} compounds...")
    dists = []
    n_fps = len(fp_list_clustering)
    
    if fp_type == 'mhfp':
        # CASE A: MHFP (Distance based on MinHash)
        for i in range(1, n_fps):
            # Distance between i and all j < i
            for j in range(i):
                dists.append(mhfp_encoder.Distance(fp_list_clustering[i], fp_list_clustering[j]))
                
    else:
        # CASE B: Bit Vectors (Distance based on 1 - Tanimoto)
        # We use BulkTanimotoSimilarity for performance optimization on large lists
        for i in range(1, n_fps):
            # Calculate similarity of i vs all previous fps (0 to i-1)
            sims = DataStructs.BulkTanimotoSimilarity(fp_list_clustering[i], fp_list_clustering[:i])
            # Convert Similarity to Distance (1 - Sim)
            dists.extend([1.0 - x for x in sims])

    # 4. Perform Butina Clustering
    # butina_cutoff is already (1 - similarity) from config, so it is a distance.
    print(f"Clustering: Running Butina algorithm with Distance Cutoff = {butina_cutoff:.2f}...")
    raw_clusters = Butina.ClusterData(dists, n_fps, butina_cutoff, isDistData=True)
    
    # 5. Map cluster IDs back to the list
    cluster_labels = [0] * n_fps
    for idx, cluster in enumerate(raw_clusters):
        for mol_idx in cluster:
            cluster_labels[mol_idx] = idx
            
    df_training_copy["butina_cluster"] = cluster_labels

    # Assign final variables for the pipeline
    fingerprints_training = np.stack(df_training_copy["fp"])
    affinity_training = df_training_copy["class"]
    cluster_list = df_training_copy["butina_cluster"]
    
    print(f"Clusters found: {max(cluster_list) + 1} with a distance cutoff: {butina_cutoff:.2f}")
    
    X, y = fingerprints_training, affinity_training
    
    if (use_external_decoys == True) and (mode == "benchmark"):
        df_decoys_copy = df_decoys.copy()
        fingerprints_decoys = np.stack(df_decoys_copy["fp"])

    data_to_save = {
        "temp_X_training.pkl": fingerprints_training,
        "temp_y_training.pkl": affinity_training,
        "temp_cluster_list_training.pkl": cluster_list,
    }

    if (use_external_decoys == True) and (mode == "benchmark"):
        data_to_save["temp_fingerprints_decoys_training.pkl"] = fingerprints_decoys

    for key, file in data_to_save.items():
        with open(key, "wb") as f:
            pickle.dump(file, f)

    print("Training set clustering labels saved to disk.\n")

############### ALGORITHM FOR BENCHMARKING ########################
if mode == "benchmark":
    fold = 0
    rep = 1

    results = pd.DataFrame()

    tp = []
    fp = []
    fp_ext = []
    fp_tot = []

    roc_aucs = []
    prc_aucs = []
    precisions = []
    f_scores = []
    bedrocs = []

    training_sets = []
    test_sets = []

    class_labels, class_counts = np.unique(np.asarray(y), return_counts=True)
    class_count_lookup = {int(label): int(count) for label, count in zip(class_labels, class_counts)}
    active_count = class_count_lookup.get(0, 0)
    inactive_count = class_count_lookup.get(1, 0)

    if active_count < 2 or inactive_count < 2:
        raise ValueError(
            "Benchmarking requires at least 2 active and 2 inactive compounds after preprocessing. "
            f"Found actives={active_count}, inactives={inactive_count}."
        )

    max_allowed_splits = min(active_count, inactive_count)
    if n_splits > max_allowed_splits:
        print(
            f"Benchmarking: Requested n_splits={n_splits} exceeds smallest class size ({max_allowed_splits}). "
            f"Using n_splits={max_allowed_splits} for this run."
        )
        n_splits = max_allowed_splits

    print("\n----BENCHMARKING CALCULATIONS----\n")

    print(
        f"Benchmarking: Calculating statistics for {n_splits} training database splits and {n_repeats} repetition(s):"
    )
    for rep in range(1, n_repeats + 1):
        # Use CORRECTED StratifiedGroupKFold
        # Using StratifiedGroupKFold ensures that:
        # 1. Clusters are kept intact (no leakage)
        # 2. Folds are balanced in size
        # 3. Class distribution (Active/Inactive) is preserved
        
        sgkf = StratifiedGroupKFold(n_splits=n_splits, shuffle=True, random_state=None)
        
        # We pass 'groups=cluster_list' which was generated by our universal clustering block above
        Ksplit = sgkf.split(X, y, groups=cluster_list)

        for train, test in Ksplit:
            gc.collect()            
            training_sets.append(train)
            test_sets.append(test)
            X_train = X[train]
            y_train = y[train]
            X_test = X[test]
            y_test = y[test]
            (
                training_a,
                testset_a_activescaled,
                testset_a_inactivescaled,
                training_i,
                testset_i_activescaled,
                testset_i_inactivescaled,
            ) = scaler(X_train, X_test, y_train, y_test)

            clf = RMDClassifier()
            clf.fit(training_a)
            clf.fit_i(training_i)

            actives_preds = clf.predict(
                testset_a_activescaled, testset_a_inactivescaled, score=True
            )
            inactives_preds = clf.predict(
                testset_i_activescaled, testset_i_inactivescaled, score=True
            )

            fold = fold + 1
            tp.append(np.mean(actives_preds["predictions"]))
            fp.append(np.mean(inactives_preds["predictions"]))

            if use_external_decoys == True:
                ext_decoys_activescaled, ext_decoys_inactivescaled = scaler_external(
                    X_train, y_train, fingerprints_decoys
                )
                ext_decoys_preds = clf.predict(
                    ext_decoys_activescaled, ext_decoys_inactivescaled, score=True
                )
                fp_ext.append(np.mean(ext_decoys_preds["predictions"]))
                inactives_preds = pd.concat(
                    [inactives_preds, ext_decoys_preds], ignore_index=True
                )
                fp_tot.append(np.mean(inactives_preds["predictions"]))

            roc_auc, prc_auc = get_auc(actives_preds, inactives_preds, rep, fold)
            roc_aucs.append(roc_auc)
            prc_aucs.append(prc_auc)
            precision, f_score, bedroc = get_precision_stats(
                actives_preds, inactives_preds
            )
            precisions.append(precision)
            f_scores.append(f_score)
            bedrocs.append(bedroc)
            print(f"\nFold {fold} - Rep {rep}:")

            # Calculate the number of true positives, false positives, true negatives and false negatives
            tp_count = np.sum(
                (actives_preds["predictions"] == 1)
                & (actives_preds["real binder"] == 1)
            )
            fp_count = np.sum(
                (inactives_preds["predictions"] == 1)
                & (inactives_preds["real binder"] == 0)
            )
            tn_count = np.sum(
                (inactives_preds["predictions"] == 0)
                & (inactives_preds["real binder"] == 0)
            )
            fn_count = np.sum(
                (actives_preds["predictions"] == 0)
                & (actives_preds["real binder"] == 1)
            )

            print(
                f"""
    ~~ True positive rate (Recall): {np.mean(actives_preds['predictions']):.3f}
    ~~ False positives rate: {np.mean(inactives_preds['predictions']):.3f}
    ~~ Precision: {precision:.3f}
    ~~ F Score: {f_score:.3f}
    ~~ ROC AUC: {roc_auc:.3f}
    ~~ PRC AUC: {prc_auc:.3f}
    ~~ BEDROC: {bedroc:.3f}
    ~~ #True Positives: {tp_count}
    ~~ #False Positives: {fp_count}
    ~~ #True Negatives: {tn_count}
    ~~ #False Negatives: {fn_count}
    """
            )

            if fold == n_splits:
                fold = 0
                rep = rep + 1

            ######## ATTEMPTS AT RAM CLEANING
            del (
                training_a,
                testset_a_activescaled,
                testset_a_inactivescaled,
                training_i,
                testset_i_activescaled,
                testset_i_inactivescaled,
            )
            del actives_preds, inactives_preds

            if use_external_decoys == True:
                del ext_decoys_activescaled, ext_decoys_inactivescaled, ext_decoys_preds

    if use_external_decoys == True:
        results_toappend = {
            "True Positives Rate": tp,
            "ROC AUC": roc_aucs,
            "PRC AUC": prc_aucs,
            "Precision": precisions,
            "F Score": f_scores,
            "BEDROC": bedrocs,
            "Internal False Positives Rate": fp,
            "External False Positives Rate": fp_ext,
            "False Positives Rate": fp_tot,
        }
        results = pd.concat(
            [results, pd.DataFrame(results_toappend)], ignore_index=True
        )
    else:
        results_toappend = {
            "True Positives Rate": tp,
            "ROC AUC": roc_aucs,
            "PRC AUC": prc_aucs,
            "Precision": precisions,
            "F Score": f_scores,
            "BEDROC": bedrocs,
            "False Positives Rate": fp,
        }
        results = pd.concat(
            [results, pd.DataFrame(results_toappend)], ignore_index=True
        )


####CONFIDENCE INTERVAL
if mode == "benchmark":

    print(
        """\n+---------------------------------------------------------+
| Averaged Benchmarking Results With Confidence Intervals |
+---------------------------------------------------------+
"""
    )
    print(f"\nTrue Positive Rate (Recall)")
    tp_ci, tp_margin = get_confidence_interval(results["True Positives Rate"])
    print(f"\nFalse Positive Rate")
    fp_ci, fp_margin = get_confidence_interval(results["False Positives Rate"])
    print(f"\nPrecision")
    precision_ci, precision_margin = get_confidence_interval(results["Precision"])
    print(f"\nF Score")
    fscore_ci, fscore_margin = get_confidence_interval(results["F Score"])
    print(f"\nROC AUC")
    roc_ci, roc_margin = get_confidence_interval(results["ROC AUC"])
    print(f"\nPRC AUC")
    prc_ci, prc_margin = get_confidence_interval(results["PRC AUC"])
    print(f"\nBEDROC")
    bedroc_ci, bedroc_margin = get_confidence_interval(results["BEDROC"])

    print("\n+---------------------------------------------------------+")

    def _slugify_metric_value(value):
        text = str(value)
        text = text.replace(".", "p")
        text = text.replace("-", "m")
        return text

    benchmark_output_dir = Path(benchmark_file).resolve().parent
    benchmark_output_dir.mkdir(parents=True, exist_ok=True)
    model_tag = (
        f"fp_{fp_type}_nb{nbits}_ea{_slugify_metric_value(threshold)}"
        f"_ei{_slugify_metric_value(threshold_i)}_inh{_slugify_metric_value(inhibition_threshold)}"
    )
    roc_curve_file = str(benchmark_output_dir / f"ROC_curve_{model_tag}.png")
    prc_curve_file = str(benchmark_output_dir / f"PRC_curve_{model_tag}.png")


###### GET REPRESENTATIVE AUC CURVE
if mode == "benchmark":

    print("\nBenchmarking: Generating representative ROC curve")
    best_diff = 100000
    for i in range(len(results["ROC AUC"])):
        auc = results["ROC AUC"][i]
        if (abs(auc - roc_ci)) < best_diff:
            best_diff = abs(auc - roc_ci)
            best_i = i
            best_rep, best_fold = get_fold_number(i)
            best_fold_auc = results["ROC AUC"][i]
    # print(f'The estimated AUC is: {auc_ci:.2f}, and the fold closest to the estimated value is Rep {best_rep} Fold {best_fold:} (index {best_i}) with an AUC of {best_fold_auc:.2f} and a difference of {best_diff:.2f})')
    train = training_sets[best_i]
    test = test_sets[best_i]

    X_train = X[train]
    y_train = y[train]
    X_test = X[test]
    y_test = y[test]
    (
        training_a,
        testset_a_activescaled,
        testset_a_inactivescaled,
        training_i,
        testset_i_activescaled,
        testset_i_inactivescaled,
    ) = scaler(X_train, X_test, y_train, y_test)
    clf = RMDClassifier()
    clf.fit(training_a)
    clf.fit_i(training_i)
    actives_preds = clf.predict(
        testset_a_activescaled, testset_a_inactivescaled, score=True
    )
    inactives_preds = clf.predict(
        testset_i_activescaled, testset_i_inactivescaled, score=True
    )

    if use_external_decoys == True:
        ext_decoys_activescaled, ext_decoys_inactivescaled = scaler_external(
            X_train, y_train, fingerprints_decoys
        )
        ext_decoys_preds = clf.predict(
            ext_decoys_activescaled, ext_decoys_inactivescaled, score=True
        )
        inactives_preds = pd.concat(
            [inactives_preds, ext_decoys_preds], ignore_index=True
        )

    roc_auc, prc_auc = get_auc(
        actives_preds,
        inactives_preds,
        best_rep,
        best_fold,
        plot_roc=True,
        roc_plot_path=roc_curve_file,
    )

    print(f"Benchmarking: ROC curve saved to {roc_curve_file}")


###### GET REPRESENTATIVE PRC CURVE
if mode == "benchmark":

    print("\nBenchmarking: Generating representative PRC curve")

    best_diff = 100000

    for i in range(len(results["PRC AUC"])):
        auc = results["PRC AUC"][i]

        if (abs(auc - prc_ci)) < best_diff:
            best_diff = abs(auc - prc_ci)
            best_i = i
            best_rep, best_fold = get_fold_number(i)
            best_fold_auc = results["PRC AUC"][i]

    train = training_sets[best_i]
    test = test_sets[best_i]

    X_train = X[train]
    y_train = y[train]
    X_test = X[test]
    y_test = y[test]

    (
        training_a,
        testset_a_activescaled,
        testset_a_inactivescaled,
        training_i,
        testset_i_activescaled,
        testset_i_inactivescaled,
    ) = scaler(X_train, X_test, y_train, y_test)

    clf = RMDClassifier()
    clf.fit(training_a)
    clf.fit_i(training_i)
    actives_preds = clf.predict(
        testset_a_activescaled, testset_a_inactivescaled, score=True
    )
    inactives_preds = clf.predict(
        testset_i_activescaled, testset_i_inactivescaled, score=True
    )

    if use_external_decoys == True:
        ext_decoys_activescaled, ext_decoys_inactivescaled = scaler_external(
            X_train, y_train, fingerprints_decoys
        )
        ext_decoys_preds = clf.predict(
            ext_decoys_activescaled, ext_decoys_inactivescaled, score=True
        )
        inactives_preds = pd.concat(
            [inactives_preds, ext_decoys_preds], ignore_index=True
        )

    roc_auc = get_auc(
        actives_preds,
        inactives_preds,
        best_rep,
        best_fold,
        plot_prc=True,
        prc_plot_path=prc_curve_file,
    )

    print(f"Benchmarking: PRC curve saved to {prc_curve_file}")
    print("Benchmarking process complete!")


############ SAVE BENCHMARK INFO IN A CSV
if mode == "benchmark":

    benchmark = pd.DataFrame()

    # Model info
    benchmark["chembl_file"] = [chembl_file]
    benchmark["activity_threshold"] = [activity_threshold]
    benchmark["inactivity_threshold"] = [inactivity_threshold]
    benchmark["inhibition_threshold"] = [inhibition_threshold]
    benchmark["roc_curve_file"] = [roc_curve_file]
    benchmark["prc_curve_file"] = [prc_curve_file]
    benchmark["epsilon_cutoff_actives"] = [threshold]
    benchmark["epsilon_cutoff_inactives"] = [threshold_i]

    benchmark["Training Actives"] = [actives_num]
    benchmark["Training Inactives"] = [inactives_num]
    benchmark["Initial Number of Decoys"] = [original_decoy_num]
    benchmark["Number of Decoys"] = [decoy_num]

    # Scores and Confidence Intervals
    benchmark["TPR"] = [round(tp_ci, 3)]
    benchmark["TPR CI"] = [round(tp_margin, 3)]

    benchmark["FPR"] = [round(fp_ci, 3)]
    benchmark["FPR CI"] = [round(fp_margin, 3)]

    benchmark["Precision"] = [round(precision_ci, 3)]
    benchmark["Precision CI"] = [round(precision_margin, 3)]

    benchmark["F Score"] = [round(fscore_ci, 3)]
    benchmark["F Score CI"] = [round(fscore_margin, 3)]

    benchmark["ROC AUC"] = [round(roc_ci, 3)]
    benchmark["ROC AUC CI"] = [round(roc_margin, 3)]

    benchmark["PRC AUC"] = [round(prc_ci, 3)]
    benchmark["PRC AUC CI"] = [round(prc_margin, 3)]

    benchmark["BEDROC"] = [round(bedroc_ci, 3)]
    benchmark["BEDROC CI"] = [round(bedroc_margin, 3)]

    # Training datasets
    benchmark["actives_file"] = [actives_file]
    benchmark["inactives_file"] = [inactives_file]

    # Fingerprints Parameters
    benchmark["fp_type"] = [fp_type]
    benchmark["explicit_hydrogens"] = [explicit_hydrogens]
    benchmark["iterations"] = [iterations]
    benchmark["nbits"] = [nbits]
    benchmark["chirality"] = [chirality]
    benchmark["redundancy"] = [redundancy]
    benchmark["features"] = [features]

    # Decoys
    benchmark["use_decoys"] = [use_external_decoys]
    benchmark["decoys_file"] = [decoys_file]
    benchmark["sample_number"] = [sample_number]

    # KFold Parameters
    benchmark["n_splits"] = [n_splits]
    benchmark["n_repeats"] = [n_repeats]

    # Stat Parameters
    benchmark["beta"] = [beta]
    benchmark["alpha"] = [alpha]

    # Convert all NaN values
    benchmark = benchmark.fillna(0)

    print(f"The benchmark results are being written in the file {benchmark_file}")

    if Path(benchmark_file).is_file():
        try:
            existing_benchmark = pd.read_csv(benchmark_file)
            merged_columns = list(existing_benchmark.columns)
            for column_name in benchmark.columns:
                if column_name not in merged_columns:
                    merged_columns.append(column_name)

            existing_benchmark = existing_benchmark.reindex(columns=merged_columns)
            benchmark = benchmark.reindex(columns=merged_columns)
            merged_benchmark = pd.concat([existing_benchmark, benchmark], ignore_index=True)
            merged_benchmark.to_csv(path_or_buf=benchmark_file, index=False)
        except Exception:
            benchmark.to_csv(
                path_or_buf=benchmark_file, index=False, mode="a", header=False
            )

    else:
        benchmark.to_csv(path_or_buf=benchmark_file, index=False)


###############~~~ EXTERNAL DB PREDICTION FUNCTION ~~~#################
def ML_prediction(
    filename,
    final_name,
    X=X,
    y=y,
    score=score,
    decoy=False,
    sample_number=sample_number,
):

    print("\n----VIRTUAL SCREENING----\n")

    df = file_reader(filename)

    df = df.sort_values(by=["Title"])
    df = df.drop_duplicates(subset="Title", keep="first")
    df = df.dropna(subset=["Smiles", "Title"])

    if decoy == True:

        if len(df["Title"]) > sample_number:
            df = df.sample(n=sample_number)

    df.reset_index(inplace=True)
    df = df.drop("index", axis=1)

    number_of_compounds = len(df["Smiles"])

    # OPTIMIZATION: Enhanced chunking for ultra-large datasets (up to 1 billion compounds)
    chunk_size = 25000

    number_of_chunks = max(
        1, (number_of_compounds + chunk_size - 1) // chunk_size
    )  # Ceiling division

    print(
        f"Screening: The dataset consists of {number_of_compounds} compounds. The dataset will be processed in {number_of_chunks} chunks"
    )

    # Prepare training projections for model compatibility checks
    training_a, training_i = scaler_light(X, y)
    expected_active_features = training_a.shape[1]
    expected_inactive_features = training_i.shape[1]

    # CHECKPOINT 2: Save the trained model to disk
    model_filename = (
        f"temp_model_{threshold}_{threshold_i}_{nbits}_"
        f"a{expected_active_features}_i{expected_inactive_features}.pkl"
    )

    if os.path.exists(model_filename):
        # Load the trained model from disk
        try:
            with open(model_filename, "rb") as file:
                clf = pickle.load(file)

            model_ok = (
                hasattr(clf, "p")
                and hasattr(clf, "p_i")
                and hasattr(clf, "vv")
                and hasattr(clf, "vv_i")
                and clf.p == expected_active_features
                and clf.p_i == expected_inactive_features
                and getattr(clf.vv, "shape", (0, 0))[0] == expected_active_features
                and getattr(clf.vv_i, "shape", (0, 0))[0] == expected_inactive_features
            )

            if model_ok:
                print("Loaded trained model from disk.\n")
            else:
                raise ValueError("Incompatible cached model dimensions")
        except Exception:
            clf = RMDClassifier()
            clf.fit(training_a)
            clf.fit_i(training_i)
            with open(model_filename, "wb") as file:
                pickle.dump(clf, file)
            print("Cached model was incompatible. Re-trained model and saved to disk.\n")
    else:
        # Train the model and save it to disk
        clf = RMDClassifier()
        clf.fit(training_a)
        clf.fit_i(training_i)
        with open(model_filename, "wb") as file:
            pickle.dump(clf, file)
        print("Trained model and saved to disk.\n")

    count = 1

    def scorer(df_chunk):
        gc.collect()

        start_time = time.time()

        print(f"\nScreening: Processing chunk {count} out of {number_of_chunks}")
        print("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
        # Use OPTIMIZED fingerprint generator
        df_chunk = get_fingerprints_ecfp(
            df_chunk, verbose=verbose, drop_zeros=False, string=False, fp_sim=True
        )
        print(f"Screening: Calculating predictions for chunk {count}....")

        smiles_chunk = df_chunk["Smiles"]
        chunk = np.stack(df_chunk["fp"])
        df_chunk.drop(columns=["fp"], inplace=True)
        chunk_b, chunk_d = scaler_external(X, y, chunk)
        del chunk

        if score == True:
            df_preds = clf.predict(chunk_b, chunk_d, score=True)
            df_chunk["predicted binder"] = df_preds["predictions"]
            df_chunk["RMD_score"] = df_preds["RMD_score"] * -1
        else:
            predictions = clf.predict(chunk_b, chunk_d)
            df_chunk["predicted binder"] = predictions

        if not (gray or inactives_similarity or temporal):
            df_chunk = df_chunk[df_chunk["predicted binder"] == 1]

        df_chunk.reset_index(inplace=True, drop=True)

        if len(df_chunk["Title"]) != 0:
            # Use CORRECTED similarity calculation
            df_chunk = calculate_similarity(df_chunk, df_actives, del_ones=False)
        else:
            df_chunk["similarity"] = np.nan
            df_chunk["most similar compound"] = np.nan

        df_chunk = df_chunk.drop(["fp_sim"], axis=1, errors='ignore')

        # Save the chunk to the final file
        if count == 1:
            df_chunk.to_csv(path_or_buf=final_name, index=False)
        elif len(df_chunk["Title"]) != 0:
            df_chunk.to_csv(path_or_buf=final_name, index=False, mode="a", header=False)

        del df_chunk, chunk_b, chunk_d, smiles_chunk

        print(f"Chunk processed in {(time.time() - start_time):.2f} seconds")

        return "Ha!"

    # OPTIMIZATION: Memory-efficient chunking for ultra-large datasets
    print(
        f"OPTIMIZATION: Processing {number_of_compounds:,} compounds in {number_of_chunks:,} chunks of {chunk_size:,} compounds each"
    )

    for chunk_start in range(0, number_of_compounds, chunk_size):
        chunk_end = min(chunk_start + chunk_size, number_of_compounds)
        df_chunk = df.iloc[chunk_start:chunk_end].copy()

        # Process chunk and clean up memory
        scorer(df_chunk)
        count = count + 1

        # Force garbage collection after each chunk for memory efficiency
        gc.collect()

        # Progress reporting for large datasets
        if number_of_compounds > 1000000:
            progress = (chunk_end / number_of_compounds) * 100
            print(
                f"OPTIMIZATION: Overall progress: {progress:.1f}% ({chunk_end:,}/{number_of_compounds:,} compounds processed)"
            )

    print("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
    print(
        f"\nPredictions complete! The results have been written to the file {screening_output}"
    )
    return "Done!"


def smi_converter(filename):
    df = file_reader(filename)

    if len(df["Title"]) == 0:
        print("No actives found!")
        return None

    if "RMD_score" in df.columns:
        df = df.drop(["RMD_score"], axis=1)

    df = df.drop(["similarity", "most similar compound", "potential_pain"], axis=1)
    df.to_csv(path_or_buf="predicted_actives.smi", index=False, header=False, sep="\t")
    print("SMI file generated!")

    ######### SDF GENERATION
    if sdf_results:
        cmdCommand = f"obabel -ismi predicted_actives.smi -osdf -h --gen3D -Opredicted_actives.sdf"

        process = subprocess.Popen(cmdCommand.split(), stdout=subprocess.PIPE)
        _, error = process.communicate()

        if error:
            print(f"Error generating SDF file: {error}")

        else:
            print("SDF file generated!")

    return "Bye!"


##### EXTERNAL DB PREDICTION
if mode == "screening":

    screen = ML_prediction(db_to_screen, screening_output, score=score)
    df_test = file_reader(screening_output)
    df_test = df_test.drop(["predicted binder"], axis=1)

    if len(df_test["Title"]) == 0:
        print("No actives found!")
        sys.exit()

    if filter_properties:
        print("Filtering compounds that do not match the specified criteria...")
        df_test = prop_filter(df_test)

    if filter_pains:
        print("Flagging potential PAINS...")
        df_test = pains_filter(df_test)

    if sdf_results:
        print("Generating .smi and .sdf files of the predicted active compounds...")

    else:
        print("Generating a .smi file of the predicted active compounds...")

    df_test.to_csv(path_or_buf=screening_output, index=False)

    smi_converter(screening_output)

    print("Screening process complete!")

sys.exit()