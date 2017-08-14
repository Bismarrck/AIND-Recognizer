import math
import statistics
import warnings

import numpy as np
from hmmlearn.hmm import GaussianHMM
from sklearn.model_selection import KFold
from asl_utils import combine_sequences


class ModelSelector(object):
    '''
    base class for model selection (strategy design pattern)
    '''

    def __init__(self,
                 all_word_sequences: dict,
                 all_word_Xlengths: dict,
                 this_word: str,
                 n_constant=3,
                 min_n_components=2,
                 max_n_components=10,
                 random_state=14,
                 verbose=False):
        self.words = all_word_sequences
        self.hwords = all_word_Xlengths
        self.sequences = all_word_sequences[this_word]
        self.X, self.lengths = all_word_Xlengths[this_word]
        self.this_word = this_word
        self.n_constant = n_constant
        self.min_n_components = min_n_components
        self.max_n_components = max_n_components
        self.random_state = random_state
        self.verbose = verbose

    def select(self):
        raise NotImplementedError

    def base_model(self, num_states):
        # with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=DeprecationWarning)
        # warnings.filterwarnings("ignore", category=RuntimeWarning)
        try:
            hmm_model = GaussianHMM(
                n_components=num_states,
                covariance_type="diag",
                n_iter=1000,
                random_state=self.random_state,
                verbose=False).fit(self.X, self.lengths)
            if self.verbose:
                print("model created for {} with {} states".format(
                    self.this_word, num_states))
            return hmm_model
        except:
            if self.verbose:
                print("failure on {} with {} states".format(
                    self.this_word, num_states))
            return None


class SelectorConstant(ModelSelector):
    """ select the model with value self.n_constant

    """

    def select(self):
        """ select based on n_constant value

        :return: GaussianHMM object
        """
        best_num_components = self.n_constant
        return self.base_model(best_num_components)


class SelectorBIC(ModelSelector):
    """
    select the model with the lowest Bayesian Information Criterion(BIC) score

    http://www2.imm.dtu.dk/courses/02433/doc/ch6_slides.pdf
    Bayesian information criteria: BIC = -2 * logL + p * logN
    """

    def select(self):
        """ select the best model for self.this_word based on
        BIC score for n between self.min_n_components and self.max_n_components

        :return: GaussianHMM object
        """
        warnings.filterwarnings("ignore", category=DeprecationWarning)

        best_score = float('inf')
        best_model = None

        for n_states in range(self.min_n_components, self.max_n_components + 1):

            try:
                N, M = self.X.shape
                model = self.base_model(num_states=n_states)
                assert isinstance(model, GaussianHMM)
                logL = model.score(self.X, self.lengths)
                p = n_states ** 2 + 2 * M * n_states - 1
                score = -2 * logL + p * np.log(N)
            except:
                pass
            else:
                if score < best_score:
                    best_score = score
                    best_model = model

        return best_model


class SelectorDIC(ModelSelector):
    '''
    select best model based on Discriminative Information Criterion

    Biem, Alain. "A model selection criterion for classification: Application
    to hmm topology optimization." Document Analysis and Recognition, 2003.
    Proceedings. Seventh International Conference on. IEEE, 2003.
    DIC = log(P(X(i)) - 1/(M-1)SUM(log(P(X(all but i))
    '''

    def select(self):
        warnings.filterwarnings("ignore", category=DeprecationWarning)

        best_score = float('-inf')
        best_model = None

        for n_states in range(self.min_n_components, self.max_n_components + 1):
            try:
                model = self.base_model(num_states=n_states)
                assert isinstance(model, GaussianHMM)
                logL = model.score(self.X, self.lengths)
                means = np.mean([
                    model.score(*self.hwords[word])
                    for word in self.words if word != self.this_word]
                )
                score = logL - means
            except:
                pass
            else:
                if score > best_score:
                    best_score = score
                    best_model = model

        return best_model


class SelectorCV(ModelSelector):
    '''
    select best model based on average log Likelihood of cross-validation folds

    '''

    def select(self):
        warnings.filterwarnings("ignore", category=DeprecationWarning)

        min_num_states = 3
        best_score = float('-inf')
        best_model = self.base_model(num_states=min_num_states)

        if len(self.sequences) < min_num_states:
            return best_model

        for n_states in range(self.min_n_components, self.max_n_components + 1):
            state_scores = []
            kf = KFold()

            for train_index, test_index in kf.split(self.sequences):
                model = self.base_model(num_states=n_states)
                assert isinstance(model, GaussianHMM)

                X_train, train_lengths = combine_sequences(
                    train_index, self.sequences)
                X_test, test_lengths = combine_sequences(
                    test_index, self.sequences)
                model.fit(X_train, train_lengths)

                try:
                    state_scores.append(model.score(X_test, test_lengths))
                except:
                    pass

            try:
                score = statistics.mean(state_scores)
            except:
                score = float('inf')

            if score > best_score:
                best_score = score
                best_model = model

        return best_model
