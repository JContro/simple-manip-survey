"""I want to create a script that gets the data from firestore and then calculates the metrics as such

    It will first get data from the collections survey_responses and conversations (see annotation analysis on how to do so)
    The it will prepare the data such that the annotated (y_true) are in the format: {uuid: [0,0,1..]} where 0 if the score is =< 4 and 1 if larger. The order of the manipulation tacticts matters and needs
    to be consistent for y_true and y_pred. 

    The data for y_pred depends on the model


def calculate_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, float]:
    """
Calculate accuracy, precision, recall, and F1 score for multi-label classification.
"""
    y_true = y_true.astype(bool)
    y_pred = y_pred.astype(bool)
    
    hamming_accuracy = np.mean(y_true == y_pred)
    subset_accuracy = accuracy_score(y_true, y_pred)
    precision, recall, f1, _ = precision_recall_fscore_support(
        y_true, 
        y_pred, 
        average='macro',
        zero_division=0
    )
    
    return {
        'hamming_accuracy': hamming_accuracy,
        'subset_accuracy': subset_accuracy,
        'precision': precision,
        'recall': recall,
        'f1': f1
    }

def calculate_statistics(values: List[float]) -> Dict:
    """
Calculate statistical measures for a list of values.
"""
    values = np.array(values)
    mean = np.mean(values)
    std = np.std(values)
    confidence_level = 0.95
    degrees_of_freedom = len(values) - 1
    t_value = stats.t.ppf((1 + confidence_level) / 2, degrees_of_freedom)
    margin_of_error = t_value * (std / np.sqrt(len(values)))
    
    return {
        'mean': mean,
        'std': std,
        'var': np.var(values),
        'confidence_interval_95': (mean - margin_of_error, mean + margin_of_error)
    }

def evaluate_model(data: pd.DataFrame, model: str) -> Dict:
    """
Evaluate the model(OpenAI or Anthropic) against Longformer results.
"""
    manipulation_types = ['peer pressure', 'reciprocity pressure', 'gaslighting', 
                         'guilt-tripping', 'emotional blackmail', 'fear enhancement', 
                         'negging', 'general']
    
    folds = data['fold'].unique()
    results_per_fold = {}
    fold_metrics = {
        'overall': {metric: [] for metric in ['hamming_accuracy', 'subset_accuracy', 'precision', 'recall', 'f1']},
        'per_manipulation': {manip: {'precision': [], 'recall': [], 'f1': []} for manip in manipulation_types}
    }
    
    for fold in folds:
        fold_data = data[data['fold'] == fold]
        
        # Prepare true and predicted values
        y_true = np.column_stack([fold_data[f'{manip}_binary_true'] for manip in manipulation_types])
        y_pred = np.column_stack([fold_data[f'{model}_{manip.lower()}_zs'] for manip in manipulation_types])
        
        

        # Calculate metrics
        overall_metrics = calculate_metrics(y_true, y_pred)
        
        

        # Calculate per-manipulation metrics
        manip_metrics = {}
        y_true = y_true.astype(bool)
        y_pred = y_pred.astype(bool)
        for i, manip in enumerate(manipulation_types):
            
            precision, recall, f1, _ = precision_recall_fscore_support(
                y_true[:, i],
                y_pred[:, i],
                average='binary',
                zero_division=0
            )
            manip_metrics[manip] = {'precision': precision, 'recall': recall, 'f1': f1}
        
        results_per_fold[f'fold_{fold}'] = {
            'overall': overall_metrics,
            'per_manipulation': manip_metrics
        }
        
        # Store metrics for statistical analysis
        for metric, value in overall_metrics.items():
            fold_metrics['overall'][metric].append(value)
        for manip, metrics in manip_metrics.items():
            for metric, value in metrics.items():
                fold_metrics['per_manipulation'][manip][metric].append(value)
    
    # Calculate statistical analysis
    statistical_analysis = {
        'overall': {metric: calculate_statistics(values) 
                   for metric, values in fold_metrics['overall'].items()},
        'per_manipulation': {manip: {metric: calculate_statistics(values) 
                                   for metric, values in metrics.items()}
                           for manip, metrics in fold_metrics['per_manipulation'].items()}
    }
    
    return {
        'per_fold': results_per_fold,
        'statistical_analysis': statistical_analysis
    }

    """
