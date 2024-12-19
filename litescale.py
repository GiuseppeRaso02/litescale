# File: litescale.py

import math
from glob import glob
from os.path import join, basename, isfile, isdir
from os import mkdir
import csv
from math import floor, gcd
import json
from collections import defaultdict

PROJECT_ROOT = 'projects/'

def project_dir(project_name):
    return join(PROJECT_ROOT, project_name)

def project_file(project_name):
    return join(project_dir(project_name), "tuples.json")

def annotation_dir(project_name):
    return join(PROJECT_ROOT, project_name, "annotations")

def annotation_file(project_name, user_name):
    return join(annotation_dir(project_name), user_name+".json")

def gold_file(project_name):
    return join(project_dir(project_name), "gold.tsv")

def make_tuples(instances, k, p):
    n = len(instances)

    while gcd(n, k) != 1:
        instances = instances[:-1]
        n = len(instances)

    tuples = dict()
    tuple_id = 0
    for j in range(p):
        for x in range(int(floor(n/k))):
            t = [(x*(k**(j+1)) + (i*(k**j))) % n for i in range(k)]
            tuples[tuple_id] = [instances[x] for x in t]
            tuple_id += 1
    return tuples

def project_list(answers=None):
    return [basename(filename) for filename in glob(PROJECT_ROOT+"*")]

def get_project(project_name):
    project_path = project_file(project_name)
    if not isfile(project_path):
        raise FileNotFoundError(f"Project file not found: {project_path}")
    with open(project_path) as f:
        project_dict = json.load(f)
        return project_dict

def get_annotations(project_name, user_name):
    project_dict = get_project(project_name)

    annotation_path = annotation_file(project_name, user_name)
    if not isfile(annotation_path):
        with open(annotation_path, "w") as fo:
            json.dump({}, fo)

    with open(annotation_path) as f:
        try:
            annotations = json.load(f)
        except json.JSONDecodeError:
            annotations = {}
    return annotations

def next_tuple(project_name, user_name):
    project_dict = get_project(project_name)
    annotations = get_annotations(project_name, user_name)

    unannotated_tuples = [(tup_id, tup) for tup_id, tup in project_dict["tuples"].items() if tup_id not in annotations]
    if unannotated_tuples:
        return unannotated_tuples[0]
    return None, None

def annotate(project_name, user_name, tup_id, answer_best, answer_worst):
    annotations = get_annotations(project_name, user_name)

    # Ensure answer_best and answer_worst are always lists, even if empty
    if answer_best is None:
        answer_best = []
    elif not isinstance(answer_best, list):
        answer_best = [answer_best]

    if answer_worst is None:
        answer_worst = []
    elif not isinstance(answer_worst, list):
        answer_worst = [answer_worst]

    annotations[tup_id] = {
        "best": answer_best,
        "worst": answer_worst
    }

    with open(annotation_file(project_name, user_name), "w") as fo:
        json.dump(annotations, fo)
    progress(project_name, user_name)

def progress(project_name, user_name):
    project_dict = get_project(project_name)
    annotations = get_annotations(project_name, user_name)
    return len(annotations), len(project_dict["tuples"])

def new_project(project_name, phenomenon, tuple_size, replication, instance_file):
    if not isfile(instance_file):
        raise FileNotFoundError(f"Instance file not found: {instance_file}")

    project_dict = {
        "project_name": project_name,
        "phenomenon": phenomenon,
        "tuple_size": tuple_size,
        "replication": replication,
        "tuples": []
    }

    instances = []
    with open(instance_file) as f:
        for line in f:
            parts = line.strip().split("\t")
            if len(parts) != 2:
                raise ValueError(f"Invalid line format in instance file: {line.strip()}")
            id, text = parts
            instances.append({"id": id, "text": text})

    project_dict['tuples'] = make_tuples(
        instances,
        tuple_size,
        replication
    )

    if not isdir(PROJECT_ROOT):
        mkdir(PROJECT_ROOT)
    if not isdir(project_dir(project_name)):
        mkdir(project_dir(project_name))
    with open(project_file(project_name), "w") as fo:
        json.dump(project_dict, fo)
    if not isdir(annotation_dir(project_name)):
        mkdir(annotation_dir(project_name))

def empty_annotation(project_name):
    annotation_list = glob(join(annotation_dir(project_name), "*.json"))

    for annotation_file in annotation_list:
        with open(annotation_file) as f:
            data = json.load(f)
            if data:
                return False
    return True

def calculate_contextual_scores(project_name):
    project_dict = get_project(project_name)

    phrase_scores = defaultdict(lambda: {"best": 0, "worst": 0, "total": 0, "contexts": set()})

    for annotation_file in glob(join(annotation_dir(project_name), "*.json")):
        user_annotations = get_annotations(project_name, basename(annotation_file).replace(".json", ""))

        for tup_id, details in user_annotations.items():
            tup = project_dict["tuples"][tup_id]
            for item in tup:
                phrase = item["text"]
                phrase_scores[phrase]["contexts"].add(phrase)

                if item["id"] in details["best"]:
                    phrase_scores[phrase]["best"] += 1
                if item["id"] in details["worst"]:
                    phrase_scores[phrase]["worst"] += 1
                phrase_scores[phrase]["total"] += 1

    scores = {}
    for phrase, score_data in phrase_scores.items():
        best = score_data["best"]
        worst = score_data["worst"]
        total = score_data["total"]

        score = (math.exp(best) - math.exp(worst)) / total if total > 0 else 0
        scores[phrase] = score

    max_score = max(scores.values()) if scores else 1
    min_score = min(scores.values()) if scores else 0

    min_score = max(min_score, 0)
    max_score = max(max_score, 0)

    normalized_scores = {}
    for phrase, score in scores.items():
        score = max(score, 0)
        normalized_score = (math.log(1 + score) - math.log(1 + min_score)) / (
                    math.log(1 + max_score) - math.log(1 + min_score)) if max_score != min_score else 0
        normalized_scores[phrase] = normalized_score

    with open(gold_file(project_name), "w") as f:
        f.write("Phrase\tScore\tContexts\n")
        for phrase, score in normalized_scores.items():
            contexts = " | ".join(sorted(phrase_scores[phrase]["contexts"]))
            f.write(f"{phrase}\t{score:.2f}\t{contexts}\n")

    print(f"Gold standard with contextual scores saved to {gold_file(project_name)}")

    return normalized_scores
