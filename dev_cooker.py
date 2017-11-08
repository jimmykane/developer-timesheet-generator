#!/usr/bin/python
import sys
import os
import json
import datetime
import csv
import math
import random

from collections import Counter
from timing import timing
from pygit2 import Repository, GIT_SORT_TOPOLOGICAL, GIT_STATUS_CURRENT, GIT_BRANCH_REMOTE, GIT_BRANCH_LOCAL

INPUT_FILE = 'projects.json'
FROM_DATE = datetime.date(2013, 07, 01)
TO_DATE = datetime.date(2014, 01, 01)


@timing
def main(argv):
    json_repos = get_repos_from_json()
    if not json_repos:
        print("Error. pickery.json does not contain any repos")
        exit(2)
        # Gather analysis of repos
    analyzed_repos = {}
    repo_keys, active_dates, repos_authors, total_commits = ([], [], [], [])
    for name_key, values in json_repos.items():
        analysis, repo_dates, repo_authors, commits = analyze_repository(Repository(values['src']), FROM_DATE, TO_DATE)
        analysis.update({'total_hours': json_repos[name_key]['total_hours']})
        active_dates = active_dates + repo_dates
        repos_authors = repos_authors + repo_authors
        total_commits = total_commits + commits
        repo_keys.append(name_key)
        analyzed_repos.update({name_key: analysis})
        # Unique
    active_dates = sorted(set(active_dates))
    repos_authors = set(repos_authors)
    print('From {0} to {1} a total of {2} active days found'.format(FROM_DATE.isoformat(), TO_DATE.isoformat(),
                                                                    str(len(active_dates))))
    print('A total of {0} repos with {1} authors overall and {2} total commits'.format(len(repo_keys),
                                                                                       len(repos_authors),
                                                                                       len(total_commits)))
    analyzed_repos = find_author_collisions(analyzed_repos, repo_keys, active_dates)
    calculate_distribution(analyzed_repos, repo_keys, active_dates, repos_authors)


def analyze_repository(repo, from_date, to_date):
    dates_and_authors_tree, authors_and_dates_tree, commits = get_dates_and_authors_trees(repo, from_date, to_date)
    analyzed_repo = {}
    repo_dates, repo_authors = ([], [])
    for date, authors in dates_and_authors_tree.items():
        analyzed_repo.update({date: authors})
        repo_dates.append(date)
        repo_authors = repo_authors + [author for author in authors]
    return analyzed_repo, repo_dates, repo_authors, commits


def get_dates_and_authors_trees(repo, from_date, to_date):
    dates_and_authors, authors_and_dates = ({}, {})
    commits = []

    all_refs = repo.listall_references()
    all_refs.remove('refs/remotes/origin/HEAD')
    # force master
    all_refs = ['refs/remotes/origin/master']
    refs_heads = [repo.lookup_reference(ref) for ref in all_refs]

    for ref_head in refs_heads:

        for commit in repo.walk(ref_head.target, GIT_SORT_TOPOLOGICAL):
            if not (datetime.date.fromtimestamp(commit.commit_time) >= from_date and not (
                    to_date < datetime.date.fromtimestamp(commit.commit_time))):
                continue
            commits.append(commit)
            # Correct multiple authors
            first_email_part = commit.author.email.split("@")[0]
            if first_email_part == 'wouter':
                first_email_part = 'wouter.de.winter'
            if first_email_part in ['dennis', 'denniswaasdorp']:
                first_email_part = 'dennis.waasdorp'
            # Trying is needed here
            try:
                # lets try to append to the set or if fail create one
                dates_and_authors[datetime.date.fromtimestamp(commit.commit_time)].update({first_email_part: {}})
            except KeyError:
                dates_and_authors[datetime.date.fromtimestamp(commit.commit_time)] = {first_email_part: {}}
                pass
            try:
                authors_and_dates[first_email_part].update({datetime.date.fromtimestamp(commit.commit_time): {}})
            except KeyError:
                authors_and_dates[first_email_part] = {datetime.date.fromtimestamp(commit.commit_time): {}}
                pass

    return dates_and_authors, authors_and_dates, commits


def find_author_collisions(analyzed_repos, repo_keys, active_dates):
    for active_date in active_dates:
        date_authors = []
        for repo_key in repo_keys:
            try:
                #flatten the lists
                date_authors = date_authors + [author for author in analyzed_repos[repo_key][active_date]]
            except KeyError:
                pass
        author_counts = Counter(date_authors)
        # Now update
        for repo_key in repo_keys:
            slots_sum = 0
            try:
                for author in analyzed_repos[repo_key][active_date]:
                    slots_sum += 1.0 / float(author_counts[author])
                    analyzed_repos[repo_key][active_date].update({author: 1.0 / float(author_counts[author])})
            except KeyError:
                pass
            try:
                analyzed_repos[repo_key].update({'slots_sum': analyzed_repos[repo_key]['slots_sum'] + slots_sum})
            except KeyError:
                analyzed_repos[repo_key].update({'slots_sum': slots_sum})
                pass
    return analyzed_repos


def calculate_distribution(analyzed_repos, repo_keys, active_dates, repos_authors):
    hours_per_day = 8.0
    max_bag = 2.0
    projects_total_hours = {}
    # 1st Case
    for repo_key in repo_keys:
        project_hours = 0
        hours_required = analyzed_repos[repo_key]['total_hours']
        units_required = float(hours_required) / float(hours_per_day)
        rows = []
        slots_sum = analyzed_repos[repo_key]['slots_sum']
        if slots_sum < units_required:
            print(repo_key + ' is not qualified to fill the corresponding hours')
            continue
        factor = units_required / slots_sum
        bag = 0.0
        for active_date in active_dates:
            row = [active_date.isoformat()]
            try:
                # try to check if the date is listed.
                analyzed_repos[repo_key][active_date]
            except KeyError:
                continue
            # here starts the cooking
            for repos_author in repos_authors:
                try:
                    slot = analyzed_repos[repo_key][active_date][repos_author]
                except KeyError:
                    row.append(repos_author)
                    row.append(0)
                    continue
                row.append(repos_author)
                val = float(slot) * float(factor) * float(hours_per_day)
                if val >= 1:
                    int_val = int(math.floor(val))
                    bag += val - float(int_val)
                else:
                    int_val = 1
                    bag -= 1.0 - val
                if bag > 1.0:
                    coin = random.choice([0,1])
                    if coin == 1 or bag > max_bag:
                        bag -= 1.0
                        int_val += 1

                project_hours += int_val
                analyzed_repos[repo_key][active_date][repos_author] = int_val
                row.append(int_val)
            rows.append(row)

        projects_total_hours.update({repo_key: project_hours})
        export_to_csv(os.path.join('projects/', repo_key), rows)
    print projects_total_hours
    print("Projects Exported")

    #second case
    for repos_author in repos_authors:
        rows = []
        for active_date in active_dates:
            row = [active_date.isoformat()]
            repos_sum = 0
            for repo_key in repo_keys:
                try:
                    repo_hours = analyzed_repos[repo_key][active_date][repos_author] # Also trigger fail
                    row.append(repo_key)
                    row.append(analyzed_repos[repo_key][active_date][repos_author])
                    repos_sum += 1
                except KeyError:
                    # if he has not worked on the repo add 0
                    row.append(repo_key)
                    row.append(0)
                    pass
            if repos_sum > 0:
                rows.append(row)
        export_to_csv(os.path.join('authors/', repos_author), rows)
    print("Authors Exported")


def export_to_csv(filename, rows):
        with open(filename + '.csv', 'w') as csv_file:
            output_writer = csv.writer(csv_file, delimiter=',', quotechar='"', quoting=csv.QUOTE_NONNUMERIC)
            for row in rows:
                output_writer.writerow(row)


def get_repos_from_json():
    with open(INPUT_FILE) as json_file:
        return json.load(json_file)


if __name__ == '__main__':
    main(sys.argv[1:])