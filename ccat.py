#!/usr/bin/env python3
import json
import sys


import boto3
import fire
from pyfiglet import figlet_format
from PyInquirer import (prompt, Separator, style_from_dict, Token)
from tabulate import tabulate


import modules.ecr__enum_repos.main as ecr__enum_repos
import modules.ecr__pull_repos.main as ecr__pull_repos
import modules.docker__backdoor.main as docker__backdoor
import modules.ecr__push_repos.main as ecr__push_repos


ENUMERATE_ECR = 'Enumerate ECR'
PULL_ECR_REPOS = 'Pull Repos from ECR'
PUSH_ECR_REPOS = 'Push Repos to ECR'
DOCKER_BACKDOOR = 'Docker Backdoor'
LIST_ECR_REPOS = 'List Enumerated ECR Repos'
SWAP_AWS_PROFILE = 'Swap AWS Profile'


custom_style = style_from_dict({
    Token.Separator: '#6C6C6C',
    Token.QuestionMark: '#FF9D00 bold',
    #Token.Selected: '',  # default
    Token.Selected: '#5F819D',
    Token.Pointer: '#FF9D00 bold',
    Token.Instruction: '',  # default
    Token.Answer: '#5F819D bold',
    Token.Question: '',
})

class CLI(object):
    def __init__(self):
        aws = AWS()
        docker = Docker()

        self.extentions = {
            'aws': aws,
            'docker': docker
        }

    def print_title(self, text='Cloud Container Attack Tool', font='slant'):
        print(figlet_format(text, font=font))

    def main_menu(self):
        menu_choices=[]
        for extention in self.extentions.values():
            menu_choices.extend(extention.get_menu())

        menu_choices += self.get_helper_menu()

        questions = [
            {
                'type': 'list',
                'name': 'main_menu',
                'message': 'What do you want to do?',
                'choices': menu_choices
            }
        ]

        answers = prompt(questions, style=custom_style)

        return answers

    def print_module_running(self, module_name):
        print('Running module {}...'.format(module_name))

    def print_module_summary(self, data, module):
        if data is not None:
            summary = module.summary(data)
            if len(summary) > 1000:
                raise ValueError('The {} module\'s summary is too long ({} characters). Reduce it to 1000 characters or fewer.'.format(module.module_info['name'], len(summary)))
            if not isinstance(summary, str):
                raise TypeError(' The {} module\'s summary is {}-type instead of str. Make summary return a string.'.format(module.module_info['name'], type(summary)))
            
            print('{} completed.\n'.format(module.module_info['name']))
            print('MODULE SUMMARY:\n\n{}\n'.format(summary.strip('\n')))  

    def run_module(self, answers):
        if ENUMERATE_ECR in answers['main_menu']:
            cli_answers = self.extentions['aws'].ask_ecr_enum_repos()
            self.print_module_running(ecr__enum_repos.module_info['name'])
            data = ecr__enum_repos.main(cli_answers)
            self.extentions['aws'].data.update({'ecr_repos': data})
            self.print_module_summary(data, ecr__enum_repos)

        elif LIST_ECR_REPOS in answers['main_menu']:
            self.extentions['aws'].print_ecr_repos()

        elif PULL_ECR_REPOS in answers['main_menu']:
            cli_answers = self.extentions['aws'].ask_ecr_pull_repos()
            self.print_module_running(ecr__pull_repos.module_info['name'])
            data = ecr__pull_repos.main(cli_answers)
            self.print_module_summary(data, ecr__pull_repos)

        elif PUSH_ECR_REPOS in answers['main_menu']:
            cli_answers = self.extentions['aws'].ask_ecr_push_repos()
            self.print_module_running(ecr__push_repos.module_info['name'])
            data = ecr__push_repos.main(cli_answers)
            self.print_module_summary(data, ecr__push_repos)

        elif DOCKER_BACKDOOR in answers['main_menu']:
            cli_answers = self.extentions['docker'].ask_docker_backdoor()
            self.print_module_running(docker__backdoor.module_info['name'])
            data = docker__backdoor.main(cli_answers)
            self.print_module_summary(data, docker__backdoor)

        elif SWAP_AWS_PROFILE in answers['main_menu']:
            self.extentions['aws'].swap_profile()

        else:
            self.exit_cli()

    def get_helper_menu(self):
        return [
            Separator(),
            'Exit'
        ]

    def exit_cli(self):
        questions = [
            {
                'type': 'confirm',
                'message': 'Do you want to exit?',
                'name': 'exit',
                'default': False,
            }
        ]

        answers = prompt(questions)
        if answers['exit']:
            print(figlet_format('Bye Bye', font='slant'))
            sys.exit()


class AWS(object):
    def __init__(self, profile=None, region=None):
        self.configuration = {
            'profile': profile,
            'region': region
        }

        self.data = {}

    def get_available_regions(self, service_name):
        aws_session = boto3.Session()
        regions = aws_session.get_available_regions(service_name)

        return regions

    def get_menu_choices_regions(self, aws_regions=[]):
        choices = []
        for region in aws_regions:
            choices.append({
                'name': region
            })

        return choices

    def get_menu(self):
        return [
            Separator('= AWS ({}) ='.format(self.configuration['profile'])),
            ENUMERATE_ECR,
            LIST_ECR_REPOS,
            PULL_ECR_REPOS,
            PUSH_ECR_REPOS,
            SWAP_AWS_PROFILE
        ]

    def swap_profile(self):
        if self.configuration.get('profile'):
            print('Current profile: {}'.format(self.configuration.get('profile')))
        self.set_configuration()

    # There could be a problem when printing 1000s of ECR repos
    def print_ecr_repos(self):
        headers = ['Repo Name', 'Repo Uri', 'Latest Tag', 'Number of Tags','Region']
        rows = []

        if self.data.get('ecr_repos') and self.data.get('ecr_repos').get('count') > 0:
            for region in self.data['ecr_repos']['payload']['aws_regions']:
                repos = self.data['ecr_repos']['payload']['repositories_by_region'][region]
                for repo in repos:
                    row = []
                    row.append(repo['repositoryName'])
                    row.append(repo['repositoryUri'])
                    # tags = []
                    tag_latest = ''
                    if repo.get('image_ids'):
                        for image_id in repo.get('image_ids'):
                            if 'imageTag' in image_id:
                                tag_latest = image_id['imageTag']
                                # tags.append(image_id['imageTag'])
                                break
                    # row.append(tags)
                    row.append(tag_latest)
                    if repo.get('image_ids'):
                        row.append(len(repo.get('image_ids')))
                    else:
                        row.append(0)
                    row.append(region)
                    rows.append(row)

        print(tabulate(rows, headers=headers,  tablefmt='orgtbl'), '\n')            

    def ask_ecr_enum_repos(self):
        if self.is_configured() is False:
            self.set_configuration()

        aws_regions = self.get_available_regions('ecr')

        questions= [
            {
                'type': 'checkbox',
                'name': 'aws_regions',
                'message': 'Select AWS regions to enumerate',
                'choices': self.get_menu_choices_regions(aws_regions)
            }
        ]

        answers = prompt(questions)
        self.append_configuration(answers)

        return answers

    def ask_ecr_pull_repos(self):
        if self.is_configured() is False:
            self.set_configuration()

        # aws_ecr_pull_all
        questions = [
            {
                'type': 'list',
                'name': 'ecr_pull_options',
                'message': 'ECR Pull Options',
                'choices': [
                    'Pull all enumerated repos',
                    'Pull single repo with multiple tags'
                ]
            }
        ]

        answers = prompt(questions)

        if 'Pull all enumerated repos' == answers.get('ecr_pull_options'):
            if self.data.get('ecr_repos') and self.data.get('ecr_repos').get('payload'):
                answers.update({
                    'ecr_repos': self.data.get('ecr_repos').get('payload')
                })
        else:
            questions = [
                {
                    'type': 'input',
                    'name': 'aws_region',
                    'message': 'Enter AWS region name'
                },
                {
                    'type': 'input',
                    'name': 'aws_ecr_repository_uri',
                    'message': 'Enter AWS ECR repository URI'
                },
                {
                    'type': 'input',
                    'name': 'aws_ecr_repository_tags',
                    'message': 'Enter AWS ECR repository tags seperated by comma'
                }
            ]

            answers = prompt(questions)

            # strip(',') remove leading or trailing (,)
            # replace(' ', '') remove spaces
            # split by comma to generate a list of tags
            answers['aws_ecr_repository_tags'] = answers['aws_ecr_repository_tags'].strip(',').replace(' ', '').split(',')
            
        self.append_configuration(answers)

        return answers

    def ask_ecr_push_repos(self):
        if self.is_configured() is False:
            self.set_configuration()

        questions = [
            {
                'type': 'input',
                'name': 'aws_region',
                'message': 'Enter AWS region name'
            },
            {
                'type': 'input',
                'name': 'aws_ecr_repository_uri',
                'message': 'Enter AWS ECR repository URI'
            },
            {
                'type': 'input',
                'name': 'aws_ecr_repository_tag',
                'message': 'Enter AWS ECR repository tag'
            }
        ]

        answers = prompt(questions)
        self.append_configuration(answers)

        return answers

    def ask_configuration(self):
        if not self.configuration.get('profile'):
            print('Did not find AWS configuration!')
            
        questions = [
            {
                'type': 'input',
                'name': 'aws_cli_profile',
                'message': 'Enter AWS profile name',
                'validate': lambda profile: len(profile) != 0 or 'AWS profile name can not be empty!'
            }
        ]

        answers = prompt(questions)

        return answers

    def set_configuration(self):
        answers = self.ask_configuration()

        print('Configuring AWS...')    
        self.configuration.update({
            'profile': answers['aws_cli_profile']
        })

        print('Successfully configured AWS\n')

    def is_configured(self):
        return self.configuration['profile'] is not None

    def print_configuration(self):
        print(json.dumps(self.configuration, indent=4, default=str))

    def append_configuration(self, answers):
        if not answers.get('aws_region'):
            answers.update({
                'aws_region': self.configuration['region']
            })

        answers.update({
            'aws_cli_profile': self.configuration['profile']
        })


class Docker(object):
    def get_menu(self):
        return [
            Separator('= Docker ='),
            DOCKER_BACKDOOR,
        ]

    def ask_docker_backdoor(self):
        print("This module generates Dockerfile on the fly and builds new Docker image.")
        questions = [
            {
                'type': 'input',
                'name': 'repository_uri',
                'message': 'Enter Docker repository name'
            },
            {
                'type': 'input',
                'name': 'target_image_tag',
                'message': 'Enter Docker repository tag'
            },
            {
                'type': 'input',
                'name': 'build_image_tag',
                'message': 'Enter new Docker repository build tag'
            }
        ]

        answers = prompt(questions)

        instructions = []
        dockerfile_from = 'FROM {}:{}\n'.format(answers['repository_uri'], answers['target_image_tag'])
        dockefile_instructions = ''
        dockerfile = dockerfile_from + dockefile_instructions

        print('\nThe below Dockerfile will be used to build a backdoored Docker image.')

        while True:
            docker_instructions_questions = [
                {
                    'type': 'input',
                    'name': 'instruction',
                    'message': 'Current Dockerfile:\n----------------\n{}\n----------------\n\nEnter Docker instruction:'.format(dockerfile)
                }
            ]         

            docker_instructions_answers = prompt(docker_instructions_questions)
            instructions.append(docker_instructions_answers['instruction'])
            dockefile_instructions = '\n'.join(instructions)
            dockerfile = dockerfile_from + dockefile_instructions

            if docker_instructions_answers['instruction']:
                continue

            print('Review:')
            print(tabulate({'Dockerfile': [dockerfile]}, headers="keys", tablefmt='orgtbl'), '\n')

            review_questions = [
                {
                    'type': 'confirm',
                    'name': 'build',
                    'message': 'Would you like to build a Docker image from above Dockerfile?',
                    'default': True,
                }
            ]

            review_answers = prompt(review_questions)

            if review_answers.get('build'):
                break
        
        answers.update({
            'dockerfile': dockerfile
        })        

        return answers


def main():
    cli = CLI()
    cli.print_title()
    while True:
        answers = cli.main_menu()
        cli.run_module(answers)


if __name__ == "__main__":
    fire.Fire(main)
