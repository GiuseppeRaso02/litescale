# File: litescale-cli.py

import json
from PyInquirer import prompt, Separator
from litescale import *
import os


def clear():
    os.system('cls' if os.name == 'nt' else 'clear')

question_main = [
    {
        'type': 'list',
        'name': 'main',
        'message': 'Welcome to Litescale',
        'choices': [
            {'name': 'Start/continue annotation',
             'value': 'start',
             'short': 'start'},
            {'name': 'Generate gold standard',
             'value': 'gold',
             'short': 'gold'},
            {'name': 'Create a new annotation project',
             'value': 'new',
             'short': 'new'},
            {'name': 'Log out',
             'value': 'logout',
             'short': 'logout'},
            Separator(),
            {'name': 'Exit',
             'value': 'exit',
             'short': 'exit'}
        ]
    }
]

questions_start = [
    {
        'type': 'list',
        'name': 'project_name',
        'message': 'Name of the project',
        'choices': project_list
    }
]

questions_new = [
    {
        'type': 'input',
        'name': 'project_name',
        'message': 'Name of the project'
    },
    {
        'type': 'input',
        'name': 'phenomenon',
        'message': 'Enter the phenomenon to annotate (e.g., offensive, positive)'
    },
    {
        'type': 'input',
        'name': 'tuple_size',
        'message': 'Dimension of the tuples',
        'validate': lambda val: val.isdigit(),
        'default': '4',
        'filter': lambda val: int(val)
    },
    {
        'type': 'input',
        'name': 'replication',
        'message': 'Replication of the instances',
        'validate': lambda val: val.isdigit(),
        'default': '4',
        'filter': lambda val: int(val)
    },
    {
        'type': 'input',
        'name': 'instance_file',
        'message': 'Read instances from tab-separated file',
        'validate': lambda val: isfile(val),
        'default': 'example.tsv'
    }
]

def prompt_bws(tup, phenomenon, best=True, exclude=[]):
    clear()
    if best:
        message = f'Which are the MOST {phenomenon}? (Select one or more, press Enter to skip)'
    else:
        message = f'Which are the LEAST {phenomenon}? (Select one or more, press Enter to skip)'
    questions_bws = [
        {
            'type': 'checkbox',
            'name': 'values',
            'message': message,
            'choices': [{"name": f"{x['text']} ", "value": x["id"], "short": x["text"]} for x in tup if x["id"] not in exclude] + [{"name": " PROGRESS", "value": "PROGRESS"}, {"name": " EXIT", "value": "EXIT"}],
            'validate': lambda answer: True if 'PROGRESS' in answer or 'EXIT' in answer or len(answer) > 0 else 'You must choose at least one option.'
        }
    ]

    return prompt(questions_bws)['values']

def prompt_progress(project_name, user_name):
    done, total = progress(project_name, user_name)
    message = f"Progress: {done}/{total} ({100.0 * (done / total):.1f}%)"
    question_progress = [
        {
            'type': 'confirm',
            'message': message,
            'name': 'continue',
            'default': True
        }
    ]
    return prompt(question_progress)['continue']

# login
def login():
    clear()
    try:
        with open(".login") as f:
            default = f.read()
    except FileNotFoundError:
        default = ""

    question_login = [
        {
            'type': 'input',
            'name': 'user_name',
            'message': 'Username:',
            'default': default
        }
    ]
    user_name = ""
    while user_name == "":
        user_name = prompt(question_login)['user_name']
    with open(".login", "w") as fo:
        fo.write(user_name)
    return user_name

user_name = login()

# main loop
while True:
    main_choice = prompt(question_main)['main']
    if main_choice == 'start':
        if len(project_list()) == 0:
            print("There are no projects.")
            continue
        project_name = prompt(questions_start)['project_name']
        project_dict = get_project(project_name)
        while True:
            tup_id, tup = next_tuple(project_name, user_name)
            if tup_id is None:
                print("There are no tuples to annotate, exiting.")
                break
            answer_best = prompt_bws(tup, project_dict["phenomenon"], best=True)
            if "EXIT" in answer_best:
                break
            if "PROGRESS" in answer_best:
                if not prompt_progress(project_name, user_name):
                    break
                continue
            if not answer_best:
                print("No selection made for 'best'. Moving to the next tuple.")
                continue

            answer_worst = prompt_bws(tup, project_dict["phenomenon"], best=False, exclude=answer_best)
            if "EXIT" in answer_worst:
                break
            if "PROGRESS" in answer_worst:
                if not prompt_progress(project_name, user_name):
                    break
                continue
            if not answer_worst:
                print("No selection made for 'worst'. Moving to the next tuple.")
                continue

            annotate(project_name, user_name, tup_id, answer_best, answer_worst)
    elif main_choice == 'gold':
        if len(project_list()) == 0:
            print("There are no projects.")
            continue
        project_name = prompt(questions_start)['project_name']
        if empty_annotation(project_name):
            print("There are no annotations, exiting.")
            continue
        calculate_contextual_scores(project_name)
    elif main_choice == 'new':
        answers = prompt(questions_new)
        new_project(
            answers['project_name'],
            answers['phenomenon'],
            answers['tuple_size'],
            answers['replication'],
            answers['instance_file']
        )
    elif main_choice == 'logout':
        user_name = login()
    elif main_choice == 'exit':
        break
