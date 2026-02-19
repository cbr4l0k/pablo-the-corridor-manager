export type SeedTaskType = {
  name: string;
  category: string;
  description: string;
  instructions: string;
  estimatedDurationMinutes?: number;
  location?: string;
};

export const TASK_TYPE_DEFINITIONS: SeedTaskType[] = [
  {
    name: "Toilet 1",
    category: "toilet",
    description: "Clean toilet 1 (the closest to the main entrance)",
    instructions:
      "1. Vacuum floor\\n2. clean toilet bowl with toilet cleaner\\n3. wipe sink, mirror & door handle\\n4. mop floor\\n5. empty trash bin\\n6. refill toilet paper if needed",
    estimatedDurationMinutes: 45,
    location: "Closest to main entrance, diagonally opposite kitchen",
  },
  {
    name: "Toilet 2",
    category: "toilet",
    description:
      "Clean toilet 2 (the one next to toilet 1 with the john deer tractor poster)",
    instructions:
      "1. Vacuum floor\\n2. clean toilet bowl with toilet cleaner\\n3. wipe sink, mirror & door handle\\n4. mop floor\\n5. empty trash bin\\n6. refill toilet paper if needed",
    estimatedDurationMinutes: 45,
    location: "Next to toilet 1, diagonally opposite kitchen",
  },
  {
    name: "Toilet 3",
    category: "toilet",
    description: "Clean toilet 3 (aka ladies toilet)",
    instructions:
      "1. Vacuum floor\\n2. clean toilet bowl with toilet cleaner\\n3. wipe sink, mirror & door handle\\n4. mop floor\\n5. empty trash bin\\n6. refill toilet paper if needed",
    estimatedDurationMinutes: 45,
    location:
      "Close to the end of the hall on the right side, after the laundry room.",
  },
  {
    name: "Toilet 4",
    category: "toilet",
    description: "Clean toilet 4 (male only toilet)",
    instructions:
      "1. Vacuum floor\\n2. clean toilet bowl with toilet cleaner\\n3. wipe sink, mirror & door handle\\n4. mop floor\\n5. empty trash bin\\n6. refill toilet paper if needed",
    estimatedDurationMinutes: 45,
    location: "Right next to toilet 3, in the very end of the hall on the right side.",
  },
  {
    name: "Shower 1",
    category: "shower",
    description: "Clean shower room 1",
    instructions:
      "1. Scrub shower walls and floor\\n2. Clean drain\\n3. Wipe mirrors and sinks\\n4. Mop floor\\n5. Empty trash",
    estimatedDurationMinutes: 60,
    location:
      "Is the shower closest to the main entrance, diagonally opposite kitchen",
  },
  {
    name: "Shower 2",
    category: "shower",
    description: "Clean shower room 2",
    instructions:
      "1. Scrub shower walls and floor\\n2. Clean drain\\n3. Wipe mirrors and sinks\\n4. Mop floor\\n5. Empty trash",
    estimatedDurationMinutes: 60,
    location: "Is the shower next to shower 1, diagonally opposite kitchen",
  },
  {
    name: "Shower 3",
    category: "shower",
    description: "Clean shower room 3",
    instructions:
      "1. Scrub shower walls and floor\\n2. Clean drain\\n3. Wipe mirrors and sinks\\n4. Mop floor\\n5. Empty trash",
    estimatedDurationMinutes: 60,
    location: "On the right wing of the corridor, in the very end of the hall",
  },
  {
    name: "Shower 4",
    category: "shower",
    description: "Clean shower room D",
    instructions:
      "1. Scrub shower walls and floor\\n2. Clean drain\\n3. Wipe mirrors and sinks\\n4. Mop floor\\n5. Empty trash",
    estimatedDurationMinutes: 60,
    location: "On the left wing of the corridor, in the very end of the hall",
  },
  {
    name: "Kitchen A",
    category: "kitchen",
    description: "Clean stove, oven & extractor hood",
    instructions: "Clean stove, oven & extractor hood. Wipe down surfaces.",
    estimatedDurationMinutes: 50,
    location: "Main kitchen",
  },
  {
    name: "Kitchen E",
    category: "kitchen",
    description: "Clean exterior surfaces",
    instructions:
      "Clean floor, walls, table, outsides of cupboards/fridges, windows, couches (also behind couch). Deep-clean (behind) stove.",
    estimatedDurationMinutes: 45,
    location: "Main kitchen",
  },
  {
    name: "Kitchen I",
    category: "kitchen",
    description: "Clean interior and dishes",
    instructions:
      "Clean insides of cupboards and microwave, sort dishes. Clean kitchen-block.",
    estimatedDurationMinutes: 35,
    location: "Main kitchen",
  },
  {
    name: "Fridge 1",
    category: "fridge",
    description: "Clean communal fridge #1",
    instructions:
      "Clean the fridge you use most. If that's in your room, you are 'Backup'.",
    estimatedDurationMinutes: 40,
    location:
      "Look for the number on the fridge, as they are not in a particular order and they are subject to change in the future.",
  },
  {
    name: "Fridge 2",
    category: "fridge",
    description: "Clean communal fridge #2",
    instructions:
      "Clean the fridge you use most. If that's in your room, you are 'Backup'.",
    estimatedDurationMinutes: 40,
    location:
      "Look for the number on the fridge, as they are not in a particular order and they are subject to change in the future.",
  },
  {
    name: "Fridge 3",
    category: "fridge",
    description: "Clean communal fridge #3",
    instructions:
      "Clean the fridge you use most. If that's in your room, you are 'Backup'.",
    estimatedDurationMinutes: 40,
    location:
      "Look for the number on the fridge, as they are not in a particular order and they are subject to change in the future.",
  },
  {
    name: "Fridge 4",
    category: "fridge",
    description: "Clean communal fridge #4",
    instructions:
      "Clean the fridge you use most. If that's in your room, you are 'Backup'.",
    estimatedDurationMinutes: 40,
    location:
      "Look for the number on the fridge, as they are not in a particular order and they are subject to change in the future.",
  },
  {
    name: "Hall Cleaning",
    category: "hallway",
    description: "Vacuum and mop floor of the hall",
    instructions:
      "Vacuum and mop the floor of Main hall and Side hall. Make pictures of stuff we don't use, remove if nobody claims/no need.",
    estimatedDurationMinutes: 40,
    location: "Entire Hall",
  },
  {
    name: "Wash Room",
    category: "laundry",
    description: "Clean laundry room",
    instructions:
      "Wash, hang and fold corridor wash. Deep-clean the machines and empty container.",
    estimatedDurationMinutes: 40,
    location: "Laundry room",
  },
  {
    name: "Trash Paper, Glass & Plastic",
    category: "trash",
    description: "Empty paper/cardboard, glass and plastic bins",
    instructions:
      "Empty the paper/cardboard, glass and plastic bins to outside containers",
    estimatedDurationMinutes: 25,
    location: "Kitchen",
  },
  {
    name: "Trash Kitchen",
    category: "trash",
    description: "Empty kitchen trash",
    instructions:
      "Empty the kitchen trash bin and clean the crates at the beginning of the hall",
    estimatedDurationMinutes: 15,
    location: "Kitchen/Hall",
  },
];
