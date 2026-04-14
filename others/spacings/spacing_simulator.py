import pandas as pd  
import numpy as np  
import yaml  
  
class SpacingSimulator:  
    """  
    Generates events for a list of person IDs based on various spacing strategies.  
    Parameters are loaded from a YAML config file.  
    """  
    def __init__(self, personids: pd.Series, yaml_path: str):  
        self.personids = personids  
        with open(yaml_path, 'r') as f:  
            self.config = yaml.safe_load(f)  
  
        self.span_days = self.config.get('span_days', None)  
        self.spacing_days = self.config.get('spacing_days', 30)  # mean spacing  
        self.spacing_multiple_max = self.config.get('spacing_multiple_max', 6)  
        self.noise = self.config.get('noise', 0)  
        self.default_probability = self.config.get('probability', 0.5)  
        self.probabilities_per_multiple = self.config.get('probabilities_per_multiple', {})  
        self.spacing_function = self.config.get('spacing_function', 'fixed_multiples')  
  
    def _generate_spacing(self, multiple=None):  
        """  
        Generate spacing based on the chosen function.  
        """  
        if self.spacing_function == 'fixed_multiples':  
            base = self.spacing_days * multiple  
        elif self.spacing_function == 'random_uniform':  
            base = np.random.uniform(0, self.span_days)  
        elif self.spacing_function == 'poisson':  
            base = np.random.poisson(self.spacing_days)  
        elif self.spacing_function == 'exponential':  
            base = np.random.exponential(scale=self.spacing_days)  
        elif self.spacing_function == 'normal':  
            base = np.random.normal(loc=self.spacing_days, scale=self.noise)  
        elif self.spacing_function == 'gamma':  
            shape = self.config.get('gamma_shape', 2)  
            scale = self.config.get('gamma_scale', self.spacing_days / shape)  
            base = np.random.gamma(shape, scale)  
        elif self.spacing_function == 'weibull':  
            shape = self.config.get('weibull_shape', 1.5)  
            scale = self.config.get('weibull_scale', self.spacing_days)  
            base = np.random.weibull(shape) * scale  
        elif self.spacing_function == 'lognormal':  
            mean = self.config.get('lognormal_mean', np.log(self.spacing_days))  
            sigma = self.config.get('lognormal_sigma', 0.5)  
            base = np.random.lognormal(mean, sigma)  
        elif self.spacing_function == 'seasonal':  
            m = multiple if multiple else 1  
            amplitude = self.config.get('seasonal_amplitude', 5)  
            period = self.config.get('seasonal_period', 12)  
            base = self.spacing_days + amplitude * np.sin(2 * np.pi * m / period)  
        elif self.spacing_function == 'custom':  
            expression = self.config.get('function_expression', '30')  
            base = eval(expression, {"np": np, "multiple": multiple})  
        else:  
            raise ValueError(f"Unknown spacing function: {self.spacing_function}")  
  
        # Add Gaussian noise if configured  
        return base + np.random.normal(loc=0, scale=self.noise)  
  
    def generate_events(self):  
        rows = []  
  
        for pid in self.personids:  
            if self.spacing_function == 'fixed_multiples' or self.spacing_function == 'seasonal':  
                for m in range(1, self.spacing_multiple_max + 1):  
                    prob = self.probabilities_per_multiple.get(m, self.default_probability)  
                    if np.random.rand() < prob:  
                        spacing_val = self._generate_spacing(m)  
                        rows.append({  
                            'personid': pid,  
                            'spacing_days': spacing_val  
                        })  
            else:  
                current_day = 0  
                while current_day < self.span_days:  
                    if np.random.rand() < self.default_probability:  
                        spacing_val = self._generate_spacing()  
                        current_day += spacing_val  
                        if current_day <= self.span_days:  
                            rows.append({  
                                'personid': pid,  
                                'spacing_days': spacing_val,  
                                'day_from_start': current_day  
                            })  
                    else:  
                        spacing_val = self._generate_spacing()  
                        current_day += spacing_val  
  
        return pd.DataFrame(rows)  