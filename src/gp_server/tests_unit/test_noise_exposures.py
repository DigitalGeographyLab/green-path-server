import gp_server.app.noise_exposures as noise_exps


def test_calculates_noise_cost_coeff():
    noises = {50: 2, 60: 4}
    db_costs = {50: 0.2, 60: 0.8}
    noise_cost_coeff = noise_exps.get_noise_cost_coeff(noises, db_costs)
    assert noise_cost_coeff == 0.6


def test_calculates_noise_exposure_index():
    length = 6
    noises = {50: 2, 60: 4}
    db_costs = {50: 0.2, 60: 0.8}
    noise_cost_coeff = noise_exps.get_noise_cost_coeff(noises, db_costs)
    noise_exposure_index = noise_exps.get_noise_exposure_index(noises, db_costs)
    assert round(noise_cost_coeff * length, 1) == round(noise_exposure_index, 1)


def test_calculates_noise_cost_1():
    length = 6
    noises = {50: 2, 60: 4}
    db_costs = {50: 0.2, 60: 0.8}
    noise_adjusted_cost = noise_exps.get_noise_adjusted_edge_cost(0.5, db_costs, noises, length)
    assert round(noise_adjusted_cost, 1) == 7.8


def test_calculates_noise_cost_2():
    length = 8.5
    noises = {50: 2, 60: 4, 70: 2.5}
    db_costs = {50: 0.2, 60: 0.8, 70: 1.3}
    noise_adjusted_cost = noise_exps.get_noise_adjusted_edge_cost(0.5, db_costs, noises, length)
    assert round(noise_adjusted_cost, 1) == 11.9


def test_calculates_low_noise_cost_for_only_40_dB():
    length = 8.5
    noises = {40: 8.5}
    db_costs = {40: 0, 50: 0.2, 60: 0.8, 70: 1.3}
    noise_adjusted_cost = noise_exps.get_noise_adjusted_edge_cost(0.5, db_costs, noises, length)
    assert round(noise_adjusted_cost, 1) == length


def test_calculates_high_noise_cost_for_missing_noises():
    length = 8.5
    noises = None
    db_costs = {50: 0.2, 60: 0.8, 70: 1.3}
    noise_cost = noise_exps.get_noise_adjusted_edge_cost(0.5, db_costs, noises, length)
    assert round(noise_cost, 1) == 433.5
