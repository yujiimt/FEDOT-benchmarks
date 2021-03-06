import csv
import datetime
import gc
import os

import numpy as np

from experiments.credit_scoring_experiment import run_credit_scoring_problem
from experiments.viz import show_history_optimization_comparison
from fedot.core.composer.optimisers.crossover import CrossoverTypesEnum
from fedot.core.composer.optimisers.gp_optimiser import GPChainOptimiserParameters, GeneticSchemeTypesEnum
from fedot.core.composer.optimisers.mutation import MutationTypesEnum
from fedot.core.composer.optimisers.regularization import RegularizationTypesEnum
from fedot.core.composer.optimisers.selection import SelectionTypesEnum
from fedot.core.utils import project_root


def write_header_to_csv(f):
    f = f'../../../tmp/{f}'
    if not os.path.isdir('../../../tmp'):
        os.mkdir('../../../tmp')
    with open(f, 'w', newline='') as file:
        writer = csv.writer(file, quoting=csv.QUOTE_ALL)
        writer.writerow(['t_opt', 'regular', 'AUC', 'n_models', 'n_layers'])


def add_result_to_csv(f, t_opt, regular, auc, n_models, n_layers):
    f = f'../../../tmp/{f}'
    with open(f, 'a', newline='') as file:
        writer = csv.writer(file, quoting=csv.QUOTE_ALL)
        writer.writerow([t_opt, regular, auc, n_models, n_layers])


def _reduced_history_best(history, generations, pop_size):
    reduced = []
    for gen in range(generations):
        fitness_values = [abs(individ) for individ in history[gen * pop_size: (gen + 1) * pop_size]]
        best = max(fitness_values)
        print(f'Min in generation #{gen}: {best}')
        reduced.append(best)

    return reduced


if __name__ == '__main__':
    max_amount_of_time = 400
    step = 400
    file_path_train = 'cases/data/scoring/scoring_train.csv'
    full_path_train = os.path.join(str(project_root()), file_path_train)
    file_path_test = 'cases/data/scoring/scoring_test.csv'
    full_path_test = os.path.join(str(project_root()), file_path_test)
    file_path_result = 'regular_exp.csv'
    history_file = 'history.csv'
    write_header_to_csv(file_path_result)
    time_amount = step
    crossover_types_set = [[CrossoverTypesEnum.subtree], [CrossoverTypesEnum.one_point],
                           [CrossoverTypesEnum.subtree, CrossoverTypesEnum.one_point], [CrossoverTypesEnum.none]]
    history_gp = [[] for _ in range(len(crossover_types_set))]
    pop_size = 20
    iterations = 20
    runs = 8
    while time_amount <= max_amount_of_time:
        for type_num, crossover_type in enumerate(crossover_types_set):
            for run in range(runs):
                gc.collect()
                selection_types = [SelectionTypesEnum.tournament]
                crossover_types = crossover_type
                mutation_types = [MutationTypesEnum.simple, MutationTypesEnum.growth, MutationTypesEnum.reduce]
                regular_type = RegularizationTypesEnum.decremental
                genetic_scheme_type = GeneticSchemeTypesEnum.steady_state
                optimiser_parameters = GPChainOptimiserParameters(selection_types=selection_types,
                                                                  crossover_types=crossover_types,
                                                                  mutation_types=mutation_types,
                                                                  regularization_type=regular_type,
                                                                  genetic_scheme_type=genetic_scheme_type)
                roc_auc, chain, composer = run_credit_scoring_problem(full_path_train, full_path_test,
                                                                      max_lead_time=datetime.timedelta(
                                                                          minutes=time_amount),
                                                                      gp_optimiser_params=optimiser_parameters,
                                                                      pop_size=pop_size, generations=iterations)

                is_regular = regular_type == RegularizationTypesEnum.decremental
                add_result_to_csv(file_path_result, time_amount, is_regular, round(roc_auc, 4), len(chain.nodes),
                                  chain.depth)
                historical_fitness = [chain.fitness for chain in composer.history]
                history_gp[type_num].append(historical_fitness)
        time_amount += step
    reduced_fitness_gp = [[] for _ in range(len(history_gp))]
    for launch_num in range(len(history_gp)):
        for history in history_gp[launch_num]:
            fitness = _reduced_history_best(history, iterations, pop_size)
            reduced_fitness_gp[launch_num].append(fitness)
    np.save('reduced_fitness_gp', reduced_fitness_gp)
    print(reduced_fitness_gp)
    m = [_ * pop_size for _ in range(iterations)]
    show_history_optimization_comparison(optimisers_fitness_history=reduced_fitness_gp,
                                         iterations=[_ for _ in range(iterations)],
                                         labels=['Subtree crossover', 'One-point crossover', 'All crossover types',
                                                 'Without crossover'])
