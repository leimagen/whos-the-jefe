const POSITIONS = {
  "working":                  { "emp_001": {x:200,y:250}, "emp_002": {x:400,y:250} },
  "focused":                  { "emp_001": {x:200,y:250}, "emp_002": {x:400,y:250} },
  "distracted":               { "emp_001": {x:230,y:290}, "emp_002": {x:430,y:290} },
  "in a meeting":             { "emp_001": {x:590,y:180}, "emp_002": {x:650,y:180} },
  "on a break":               { "emp_001": {x:620,y:410}, "emp_002": {x:680,y:410} },
  "chatting with a coworker": { "emp_001": {x:290,y:310}, "emp_002": {x:350,y:310} }
};

const REMOTE_SPRITE_POS = {
  "emp_003": {x: 105, y: 450}
};

const REMOTE_EMPLOYEES = ["emp_003"];

class OfficeScene extends Phaser.Scene {
  constructor() {
    super({ key: "OfficeScene" });
    this.employeeSprites = {};
  }

  preload() {
    this.load.spritesheet("maria", "/assets/character-female1.png", {
      frameWidth: 16, frameHeight: 32
    });
    this.load.spritesheet("james", "/assets/character-male1.png", {
      frameWidth: 16, frameHeight: 32
    });
    this.load.spritesheet("lu", "/assets/character-male2.png", {
      frameWidth: 16, frameHeight: 32
    });
    this.load.image("chair", "/assets/chair-red.png");
    this.load.image("workstation", "/assets/workstation.png");
  }

  create() {
    // Floor — depth 0 (default)
    this.add.rectangle(400, 300, 800, 600, 0x2d2d44);

    // Chairs — depth 1 (behind workstation and employee)
    this.add.image(200, 250, "chair").setScale(2).setDepth(1);
    this.add.image(400, 250, "chair").setScale(2).setDepth(1);

    // Workstations — depth 3 (in front of employee when at desk)
    this.add.image(200, 265, "workstation").setScale(2).setDepth(3);
    this.add.image(400, 265, "workstation").setScale(2).setDepth(3);

    // Meeting room
    this.add.rectangle(620, 180, 150, 100, 0x3a3a5c);

    // Break area
    this.add.rectangle(650, 420, 120, 80, 0x3a3a5c);

    // Remote zone — bottom left, distinct color
    this.add.rectangle(105, 470, 170, 110, 0x1a2a3a);
    // Dashed border effect — inner rectangle slightly smaller
    this.add.rectangle(105, 470, 166, 106, 0x1a2a3a).setStrokeStyle(1, 0x38bdf8, 0.4);

    // Animations
    ["maria", "james", "lu"].forEach(key => {
      const blinkRate = Phaser.Math.Between(3, 9);
      this.anims.create({
        key: `${key}_blink`,
        frames: [
          { key, frame: 0 }, { key, frame: 0 }, { key, frame: 0 }, { key, frame: 0 },
          { key, frame: 0 }, { key, frame: 0 }, { key, frame: 0 }, { key, frame: 0 },
          { key, frame: 3 }
        ],
        frameRate: blinkRate, repeat: -1
      });
      this.anims.create({ key: `${key}_idle_front`, frames: [{ key, frame: 0 }], frameRate: 1, repeat: -1 });
      this.anims.create({ key: `${key}_walk_front`, frames: this.anims.generateFrameNumbers(key, { start: 1, end: 2 }), frameRate: 6, repeat: -1 });
      this.anims.create({ key: `${key}_idle_side`, frames: [{ key, frame: 4 }], frameRate: 1, repeat: -1 });
      this.anims.create({ key: `${key}_walk_side`, frames: this.anims.generateFrameNumbers(key, { start: 5, end: 6 }), frameRate: 6, repeat: -1 });
      this.anims.create({ key: `${key}_idle_back`, frames: [{ key, frame: 8 }], frameRate: 1, repeat: -1 });
      this.anims.create({ key: `${key}_walk_back`, frames: this.anims.generateFrameNumbers(key, { start: 9, end: 10 }), frameRate: 6, repeat: -1 });
    });

    // Presential employees
    this.createEmployee("emp_001", 200, 250, "maria");
    this.createEmployee("emp_002", 400, 250, "james");

    // Remote employees — fixed position
    this.createEmployee("emp_003", REMOTE_SPRITE_POS["emp_003"].x, REMOTE_SPRITE_POS["emp_003"].y, "lu");

    this.time.addEvent({ delay: 3000, callback: this.pollState, callbackScope: this, loop: true });
  }

  createEmployee(id, x, y, textureKey) {
    const sprite = this.add.sprite(x, y, textureKey, 0);
    sprite.setScale(3);
    sprite.textureKey = textureKey;
    sprite.currentDirection = "front";
    sprite.setDepth(2);
    sprite.play(`${textureKey}_blink`);
    this.employeeSprites[id] = sprite;
  }

  moveEmployeeTo(id, activity) {
    // Remote employees don't move
    if (REMOTE_EMPLOYEES.includes(id)) return;

    const pos = POSITIONS[activity]?.[id];
    const sprite = this.employeeSprites[id];
    if (!pos || !sprite) return;

    const key = sprite.textureKey;
    const dx = pos.x - sprite.x;
    const dy = pos.y - sprite.y;
    const moving = Math.abs(dx) > 5 || Math.abs(dy) > 5;

    if (moving) {
      if (Math.abs(dx) > Math.abs(dy)) {
        sprite.play(`${key}_walk_side`, true);
        sprite.setFlipX(dx < 0);
      } else {
        sprite.play(dy > 0 ? `${key}_walk_front` : `${key}_walk_back`, true);
        sprite.setFlipX(false);
      }
    }

    this.tweens.add({
      targets: sprite,
      x: pos.x, y: pos.y,
      duration: 800, ease: "Power2",
      onComplete: () => {
        sprite.setFlipX(false);
        if (activity === "chatting with a coworker") {
          sprite.play(`${key}_idle_side`, true);
          // emp_001 faces right, emp_002 faces left
          if (id === "emp_001") sprite.setFlipX(false);
          if (id === "emp_002") sprite.setFlipX(true);
        } else {
          sprite.play(`${key}_blink`, true);
        }
        sprite.currentDirection = activity === "chatting with a coworker" ? "side" : "front";
      }
    });

    // Adjust depth based on activity
    const atDesk = activity === "working" || activity === "focused";
    sprite.setDepth(atDesk ? 2 : 4);
  }

  pollState() {
    fetch("/simulator/state.json")
      .then(r => r.json())
      .then(state => {
        state.employees.forEach(emp => {
          const sprite = this.employeeSprites[emp.id];
          if (sprite) {
            this.moveEmployeeTo(emp.id, emp.current_activity);
            const atDesk = emp.current_activity === "working" || emp.current_activity === "focused";
            sprite.setDepth(atDesk ? 2 : 4);
          }
        });
      })
      .catch(err => console.log("State not loaded:", err));
  }
}

const config = {
  type: Phaser.AUTO,
  width: 800,
  height: 600,
  backgroundColor: "#1a1a2e",
  pixelArt: true,
  scene: OfficeScene
};

new Phaser.Game(config);