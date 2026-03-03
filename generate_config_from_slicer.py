import xml.etree.ElementTree as ET
import os
import argparse
import sys
import copy

try:
    import yaml
except ImportError:
    yaml = None

def parse_references(ref_str):
    """Parse the Slicer references string into a dictionary."""
    if not ref_str: return {}
    refs = {}
    for part in ref_str.split(';'):
        if ':' in part:
            key, val = part.split(':', 1)
            refs[key] = val.split()
    return refs

def create_camel_case(name):
    # e.g., 'injector_device' -> 'InjectorDevice', 'case-108831' -> 'Case108831'
    pieces = name.replace('-', '_').split('_')
    return ''.join([p.capitalize() for p in pieces if p])

def create_abbreviation(camel_name):
    # e.g., 'InjectorDevice' -> 'ID', 'Case108831' -> 'C'
    abbr = ''.join([c for c in camel_name if c.isupper()])
    if not abbr and camel_name:
        abbr = camel_name[:2].upper()
    return abbr if abbr else "OBJ"

def parse_mrml(mrml_path):
    tree = ET.parse(mrml_path)
    root = tree.getroot()

    # Step 1: Extract all Storage Nodes to map Storage ID -> File Name
    storage_map = {}
    for elem in root:
        if 'Storage' in elem.tag:
            node_id = elem.get('id')
            file_name = elem.get('fileName', '')
            if node_id and file_name:
                storage_map[node_id] = file_name

    def get_info(elem):
        """Extract standardized info from a MRML node element."""
        refs = parse_references(elem.get('references'))
        
        # Find associated storage IDs
        storage_ids = refs.get('storage', [])
        # Backwards compatibility check
        if not storage_ids and elem.get('storageNodeRef'):
            storage_ids = [elem.get('storageNodeRef')]
        
        # Find associated transform ID
        transform_ids = refs.get('transform', [])
        if not transform_ids and elem.get('transformNodeRef'):
            transform_ids = [elem.get('transformNodeRef')]
        
        file_name = storage_map.get(storage_ids[0]) if storage_ids else None
        if file_name:
            import urllib.parse
            # Slicer MRML files sometimes URL-encode the file names (e.g. %20 for space)
            file_name = urllib.parse.unquote(file_name)
            # Resolve to absolute path based on MRML file location
            if not os.path.isabs(file_name):
                mrml_dir = os.path.dirname(os.path.abspath(mrml_path))
                file_name = os.path.normpath(os.path.join(mrml_dir, file_name))

        transform_id = transform_ids[0] if transform_ids else None
        
        return {
            'id': elem.get('id'),
            'name': elem.get('name'),
            'file_name': file_name,
            'transform_id': transform_id
        }

    # Step 2: Extract all relevant nodes
    items = []
    transforms = {}
    
    for elem in root:
        tag = elem.tag
        # Identify Transforms
        if 'Transform' in tag and 'Storage' not in tag and 'Display' not in tag:
            info = get_info(elem)
            info['type'] = 'Transform'
            info['matrix'] = elem.get('matrixTransformToParent')
            transforms[info['id']] = info

        # Identify Volumes
        elif 'Volume' in tag and 'Storage' not in tag and 'Display' not in tag and 'Property' not in tag:
            info = get_info(elem)
            info['type'] = 'Volume'
            if info['file_name']: items.append(info)

        # Identify Segmentations
        elif 'Segmentation' in tag and 'Storage' not in tag and 'Display' not in tag:
            info = get_info(elem)
            info['type'] = 'Segmentation'
            if info['file_name']: items.append(info)

        # Identify Landmarks (Fiducials)
        elif 'MarkupsFiducial' in tag and 'Storage' not in tag and 'Display' not in tag:
            info = get_info(elem)
            info['type'] = 'Landmarks'
            if info['file_name']: items.append(info)

        # Identify Models (3D Meshes like STL/OBJ)
        elif 'Model' in tag and 'Storage' not in tag and 'Display' not in tag and 'Hierarchy' not in tag:
            info = get_info(elem)
            info['type'] = 'Model'
            if info['file_name']: items.append(info)

    # Step 3: Group items by common identifying prefix
    groups = {}
    
    for item in items:
        name = item['name']
        
        # 1. Strip file extensions that sometimes bleed into Slicer node names
        base_name = name
        for ext in ['.nii.gz', '.nii', '.nrrd', '.seg.nrrd', '.fcsv', '.txt', '.stl', '.obj', '.ply']:
            if base_name.lower().endswith(ext):
                base_name = base_name[:-len(ext)]
                
        # 2. Split by common delimiters
        pieces = base_name.replace('-', '_').replace(' ', '_').split('_')
        
        # 3. Remove identifying suffixes if common
        suffixes = ['ct', 'seg', 'segmentation', 'landmarks', '3d', '2d', 'volume', 'model', 'mesh', 'xray']
        filtered = [p for p in pieces if p.lower() not in suffixes]
        group_key = '_'.join(filtered) if filtered else name

        if group_key not in groups:
            groups[group_key] = {
                'object_name': group_key,
                'ct': None,
                'segmentation': None,
                'landmarks': None,
                'model': None,
                'transform_id': None
            }
            
        # Assign attributes based on node type
        if item['type'] == 'Volume':
            groups[group_key]['ct'] = item['file_name']
            if item['transform_id']:
                groups[group_key]['transform_id'] = item['transform_id']
                
        elif item['type'] == 'Segmentation':
            groups[group_key]['segmentation'] = item['file_name']
            if item['transform_id'] and not groups[group_key]['transform_id']:
                groups[group_key]['transform_id'] = item['transform_id']
            
        elif item['type'] == 'Landmarks':
            groups[group_key]['landmarks'] = item['file_name']
            if item['transform_id'] and not groups[group_key]['transform_id']:
                groups[group_key]['transform_id'] = item['transform_id']

        elif item['type'] == 'Model':
            groups[group_key]['model'] = item['file_name']
            if item['transform_id'] and not groups[group_key]['transform_id']:
                groups[group_key]['transform_id'] = item['transform_id']

    # Step 4: Build Config structure
    config = {
        'logging_level': 'INFO',
        'recording_dir': 'visualizer_outputs/recordings',
        'frames': [],
        'transforms': []
    }

    used_transforms = {} # transform_id -> list of frame names using it

    for group_key, data in groups.items():
        frame_name = create_camel_case(data['object_name'])
        frame_abbr = create_abbreviation(frame_name)
        
        frame = {
            'name': frame_name,
            'abbreviation': frame_abbr,
            'type': 'model',
            'paths': {}
        }
        if data['ct']:
            frame['paths']['ct'] = data['ct']
        if data['model']:
            frame['paths']['model'] = data['model']
        if data['segmentation']:
            frame['paths']['segmentation'] = data['segmentation']
        if data['landmarks']:
            frame['paths']['landmarks'] = data['landmarks']
            
        config['frames'].append(frame)
        
        # Track transform
        t_id = data['transform_id']
        if t_id and t_id in transforms:
            if t_id not in used_transforms:
                used_transforms[t_id] = []
            used_transforms[t_id].append(frame_name)

    # Add virtual frames and transforms
    for t_id, frame_names in used_transforms.items():
        t_info = transforms[t_id]
        raw_matrix = t_info['matrix']
        
        # parse raw_matrix from string "m00 m01 m02 m03 m10 m11 m12 m13 ..." to 4x4 array
        if raw_matrix:
            nums = [float(x) for x in raw_matrix.split()]
        else:
            nums = [1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0]

        if len(nums) == 16:
            import numpy as np
            m_ras = np.array([
                nums[0:4],
                nums[4:8],
                nums[8:12],
                nums[12:16]
            ])
            # Slicer exports LinearTransform nodes as RAS-to-RAS transforms.
            # Our visualizer uses LPS. The conversion is M_LPS = C * M_RAS * C
            # where C = diag([-1, -1, 1, 1])
            C = np.diag([-1, -1, 1, 1])
            m_lps = C @ m_ras @ C
            
            # Convert back to nested python list of floats
            matrix_4x4 = m_lps.tolist()
        else:
            # fallback to identity
            matrix_4x4 = [
                [1.0, 0.0, 0.0, 0.0],
                [0.0, 1.0, 0.0, 0.0],
                [0.0, 0.0, 1.0, 0.0],
                [0.0, 0.0, 0.0, 1.0]
            ]
        
        parent_name = 'World'

        # If transform has a parent transform, ideally we would link to it, but for our simple grouping:
        # We assume 1-level hierarchy to World for simplicity in visualizer init, 
        # unless Slicer specifically had a long chain (which we could parse, but medical scenes are normally 1 level)

        if len(frame_names) == 1:
            child_name = frame_names[0]
            t_name = f"{parent_name}_from_{child_name}"
            config['transforms'].append({
                'name': t_name,
                'parent': parent_name,
                'child': child_name,
                'initial_transform': matrix_4x4
            })
        else:
            # Shared transform -> Create a virtual frame
            v_frame_name = create_camel_case(t_info['name'])
            v_frame_abbr = create_abbreviation(v_frame_name)
            
            # Prevent duplicate virtual frames if multiple shared transforms somehow collide in name
            existing = [f for f in config['frames'] if f['name'] == v_frame_name]
            if existing:
                v_frame_name += "Frame"
                v_frame_abbr += "F"

            config['frames'].append({
                'name': v_frame_name,
                'abbreviation': v_frame_abbr,
                'type': 'virtual',
                'movable': False
            })
            
            config['transforms'].append({
                'name': f"{parent_name}_from_{v_frame_name}",
                'parent': parent_name,
                'child': v_frame_name,
                'initial_transform': matrix_4x4
            })
            
            # Connect all children to this virtual frame (identity initial_transform)
            for child_name in frame_names:
                config['transforms'].append({
                    'name': f"{v_frame_name}_from_{child_name}",
                    'parent': v_frame_name,
                    'child': child_name
                })

    return config

# A custom representer for pyyaml to output matrices in an inline flow style instead of a giant vertical list
class IndentDumper(yaml.Dumper):
    pass

def represent_list(dumper, data):
    flow_style = False
    if all(isinstance(i, (int, float)) for i in data):
        flow_style = True
    return dumper.represent_sequence('tag:yaml.org,2002:seq', data, flow_style=flow_style)

if yaml is not None:
    IndentDumper.add_representer(list, represent_list)

def main():
    parser = argparse.ArgumentParser(description="Extract objects from 3D Slicer MRML scene to BiGSS Visualizer Config")
    parser.add_argument("mrml_path", help="Path to the .mrml file or a directory containing exactly one .mrml file")
    parser.add_argument("--output", "-o", help="Output .yaml config file path. Defaults to printing to stdout.")
    args = parser.parse_args()
    
    mrml_path = args.mrml_path
    
    if os.path.isdir(mrml_path):
        mrmls = [f for f in os.listdir(mrml_path) if f.endswith('.mrml')]
        if len(mrmls) == 0:
            print(f"Error: No .mrml file found in {mrml_path}")
            sys.exit(1)
        elif len(mrmls) > 1:
            print(f"Error: Multiple .mrml files found in {mrml_path}, please specify the exact file.")
            sys.exit(1)
        mrml_path = os.path.join(mrml_path, mrmls[0])

    if not os.path.exists(mrml_path):
        print(f"Error: Could not find file {mrml_path}")
        sys.exit(1)

    structured_data = parse_mrml(mrml_path)

    # Print or Save
    if args.output:
        if yaml is not None:
            with open(args.output, 'w') as f:
                yaml.dump(structured_data, f, Dumper=IndentDumper, sort_keys=False)
        else:
            import json
            with open(args.output, 'w') as f:
                json.dump(structured_data, f, indent=2)
        print(f"Config successfully saved to {args.output}")
    else:
        if yaml is not None:
            print(yaml.dump(structured_data, Dumper=IndentDumper, sort_keys=False))
        else:
            import json
            print(json.dumps(structured_data, indent=2))

if __name__ == "__main__":
    main()
