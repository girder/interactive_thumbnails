import { vec3, mat4 } from 'gl-matrix';

// ----------------------------------------------------------------------------

function snap(angle, angleStep) {
  const rest = angle % angleStep;
  if (rest > angleStep * 0.5) {
    return Math.round(angle + angleStep - rest);
  }
  return Math.round(angle - rest);
}

// ----------------------------------------------------------------------------

function getScreenEventPositionFor(event) {
  const c = event.currentTarget;
  const bounds = c.getBoundingClientRect();
  const position = [
    event.clientX - bounds.left,
    bounds.height - event.clientY + bounds.top,
    bounds.width,
    bounds.height,
  ];
  return position;
}

// ----------------------------------------------------------------------------

function floatToByte(number) {
  return (number + 1) * 255 * 0.5;
}
// ----------------------------------------------------------------------------

function byteToFloat(number) {
  return number / 255 * 2 - 1;
}

// ----------------------------------------------------------------------------

function encodeVec3(vector) {
  return btoa(String.fromCharCode.apply(null, vector.map(floatToByte)));
}

// ----------------------------------------------------------------------------

function decodeVec3(out, base64) {
  vec3.normalize(
    out,
    atob(base64)
      .split('')
      .map((c) => c.charCodeAt(0))
      .map(byteToFloat)
  );
}

// ----------------------------------------------------------------------------

function updateOrientation() {
  this.style.transform = this.dataset.rotation;
}

// ----------------------------------------------------------------------------

const trans = new Float64Array(16);
const v2 = new Float64Array(3);
const direction = new Float64Array(3);
const newCamPos = new Float64Array(3);
const newViewUp = new Float64Array(3);

// ----------------------------------------------------------------------------

export default class CinemaThumbnail {
  constructor(el, basepath, angleStep) {
    this.container = el;
    this.basepath = basepath;
    this.angleStep = angleStep;

    this.deferRoll = true; // Wait for image loaded before apply roll
    this.epsilon = Math.sin(this.angleStep / 360 * Math.PI);
    this.position = [0, 0, 1];
    this.viewUp = [0, 1, 0];
    this.rotationFactor = 1;
    this.lastPosition = [0, 0];

    this.onMouseMove = (e) => {
      e.preventDefault();
      const newPosition = getScreenEventPositionFor(e);
      if (e.which === 1) {
        if (e.shiftKey) {
          this.roll(...newPosition);
        } else {
          this.rotate(...newPosition);
        }
      }
      this.lastPosition = newPosition;
    };

    // DOM binding
    this.image = new Image();
    this.image.style.width = '100%';

    if (this.deferRoll) {
      this.image.onload = updateOrientation;
    }

    this.container.style.overflow = 'hidden';
    this.container.appendChild(this.image);
    this.container.addEventListener('mousemove', this.onMouseMove);

    // Reload state if available
    this.setState(el.dataset.state);

    this.updateImage();
  }

  free() {
    // Add mouse listener
    this.container.removeEventListener('mousemove', this.onMouseMove);
    this.container.removeChild(this.image);
    this.image = null;
    this.container = null;
    this.onMouseMove = null;
  }

  orthogonalizeViewUp() {
    vec3.cross(direction, this.position, this.viewUp);
    vec3.cross(this.viewUp, direction, this.position);
    vec3.normalize(this.viewUp, this.viewUp);
    vec3.normalize(this.position, this.position);
  }

  rotate(x, y, width, height) {
    const dx = this.lastPosition[0] - x;
    const dy = this.lastPosition[1] - y;
    mat4.identity(trans);

    // Azimuth
    mat4.rotate(
      trans,
      trans,
      this.rotationFactor * Math.PI * 2 * dx / width,
      this.viewUp
    );

    // Elevation
    vec3.cross(v2, this.viewUp, this.position);
    mat4.rotate(
      trans,
      trans,
      -this.rotationFactor * Math.PI * 2 * dy / height,
      v2
    );

    // Apply transformation to camera position, focal point, and view up
    vec3.transformMat4(newCamPos, this.position, trans);
    direction[0] = this.viewUp[0] + this.position[0];
    direction[1] = this.viewUp[1] + this.position[1];
    direction[2] = this.viewUp[2] + this.position[2];
    vec3.transformMat4(newViewUp, direction, trans);

    vec3.copy(this.position, newCamPos);

    newViewUp[0] -= newCamPos[0];
    newViewUp[1] -= newCamPos[1];
    newViewUp[2] -= newCamPos[2];
    vec3.copy(this.viewUp, newViewUp);
    this.orthogonalizeViewUp();
    this.updateImage();
  }

  roll(x, y, width, height) {
    let angle = this.rotationFactor * 2 * Math.PI;
    const dx = this.lastPosition[0] - x;
    const dy = this.lastPosition[1] - y;
    if (Math.abs(dx) > Math.abs(dy)) {
      angle *= dx / width;
      if (y < height * 0.5) {
        angle *= -1;
      }
    } else {
      angle *= dy / height;
      if (x > width * 0.5) {
        angle *= -1;
      }
    }

    if (angle === 0) {
      return;
    }

    // roll
    mat4.identity(trans);
    mat4.rotate(trans, trans, -angle, this.position);

    // Apply transformation to camera position, focal point, and view up
    vec3.transformMat4(newCamPos, this.position, trans);

    direction[0] = this.viewUp[0] + this.position[0];
    direction[1] = this.viewUp[1] + this.position[1];
    direction[2] = this.viewUp[2] + this.position[2];
    vec3.transformMat4(newViewUp, direction, trans);

    vec3.copy(this.position, newCamPos);
    newViewUp[0] -= newCamPos[0];
    newViewUp[1] -= newCamPos[1];
    newViewUp[2] -= newCamPos[2];
    vec3.copy(this.viewUp, newViewUp);
    this.orthogonalizeViewUp();
    this.updateImage();
  }

  updateImage() {
    if (!this.image) {
      return;
    }

    vec3.copy(newCamPos, this.position);
    let theta = snap(
      Math.asin(newCamPos[1]) * 180 / Math.PI + 90,
      this.angleStep
    );
    newCamPos[1] = 0;
    vec3.normalize(newCamPos, newCamPos);
    let phi = snap(Math.asin(-newCamPos[0]) * 180 / Math.PI, this.angleStep);

    if (newCamPos[2] > -this.epsilon) {
      if (phi < 0) {
        phi += 360;
      }
    } else {
      phi = 180 - phi;
    }

    if (theta < 1) {
      theta = 1;
    }
    if (theta > 179) {
      theta = 179;
    }

    const originalPosition = [
      -Math.cos((theta - 90) / 180 * Math.PI) * Math.sin(phi / 180 * Math.PI),
      Math.sin((theta - 90) / 180 * Math.PI),
      Math.cos((theta - 90) / 180 * Math.PI) * Math.cos(phi / 180 * Math.PI),
    ];

    const originalViewUp = [0, 1, 0];
    vec3.cross(originalViewUp, originalViewUp, originalPosition);
    vec3.cross(originalViewUp, originalPosition, originalViewUp);
    vec3.normalize(originalViewUp, originalViewUp);

    const correctedViewUp = [0, 0, 0];
    vec3.cross(correctedViewUp, this.viewUp, originalPosition);
    vec3.cross(correctedViewUp, originalPosition, correctedViewUp);
    vec3.normalize(correctedViewUp, correctedViewUp);

    const crossV = [0, 0, 0];
    vec3.cross(crossV, originalViewUp, correctedViewUp);
    const sign = Math.sign(vec3.dot(crossV, originalPosition));

    const cosT = vec3.dot(originalViewUp, correctedViewUp);
    const angle = sign * Math.round(Math.acos(cosT) * 180 / Math.PI);

    this.image.src = `${this.basepath}/${theta}_${phi}.jpg`;
    if (this.deferRoll) {
      this.image.dataset.rotation = `rotate(${angle}deg)`;
    } else {
      this.image.style.transform = `rotate(${angle}deg)`;
    }

    this.image.dataset.state = this.getState();
  }

  getState() {
    return [encodeVec3(this.position), encodeVec3(this.viewUp)].join('');
  }

  setState(str) {
    if (!str) {
      return;
    }
    decodeVec3(this.position, str.substring(0, 4));
    decodeVec3(this.viewUp, str.substring(4, 8));
    this.orthogonalizeViewUp();
  }
}
