import os
import sys
import importlib.util
from typing import Dict, Any

class AutoFeatureGenerator:
    """
    Takes a scientifically validated Hypothesis and physically writes 
    the Python logic into a module, then executes it to generate features.
    """
    def __init__(self, output_dir="core/agents/signal_agents/generated"):
        self.output_dir = os.path.abspath(output_dir)
        os.makedirs(self.output_dir, exist_ok=True)
        # Create __init__.py if it doesn't exist to make it a package
        init_path = os.path.join(self.output_dir, "__init__.py")
        if not os.path.exists(init_path):
            with open(init_path, 'w') as f:
                f.write("")
                
    def write_feature_module(self, hypothesis: Dict[str, Any]) -> str:
        """
        Writes the validated python logic to a physical python file.
        Returns the absolute path to the generated module.
        """
        name = hypothesis['hypothesis_name'].lower().replace(" ", "_")
        file_path = os.path.join(self.output_dir, f"hyp_{name}.py")
        
        # The LLM outputs the core logic. We wrap it in a standard class.
        python_logic = hypothesis['python_logic']
        
        module_code = f'\"\"\"\nAuto-Generated Feature Module: {hypothesis["hypothesis_name"]}\n'
        module_code += f'Description: {hypothesis["description"]}\n\"\"\"\n\n'
        module_code += "import pandas as pd\n\n"
        module_code += f"{python_logic}\n\n"
        module_code += "class GeneratedFeature:\n"
        module_code += "    def compute_features(self, df_or_row):\n"
        module_code += "        # Handles either a single dictionary row or a full pandas DataFrame\n"
        module_code += "        if isinstance(df_or_row, dict):\n"
        module_code += "            return extract(df_or_row)\n"
        module_code += "        elif hasattr(df_or_row, 'apply'):\n"
        module_code += "            # Apply over rows\n"
        module_code += "            res = df_or_row.apply(lambda r: pd.Series(extract(r.to_dict())), axis=1)\n"
        module_code += "            return pd.concat([df_or_row, res], axis=1)\n"
        module_code += "        return df_or_row\n"
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(module_code)
            
        return file_path
        
    def load_and_execute(self, file_path: str, data):
        """
        Dynamically imports the generated python module and applies it to the data.
        """
        module_name = os.path.basename(file_path).replace(".py", "")
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        
        feature_class = module.GeneratedFeature()
        return feature_class.compute_features(data)

if __name__ == "__main__":
    # Test
    generator = AutoFeatureGenerator()
    hyp = {
        "hypothesis_name": "test_feature",
        "description": "A simple test feature.",
        "python_logic": "def extract(doc):\n    return {'test_val': doc.get('id', 0) * 2}"
    }
    path = generator.write_feature_module(hyp)
    print(f"Generated module at: {path}")
    
    res = generator.load_and_execute(path, {"id": 21})
    print("Result:", res)
