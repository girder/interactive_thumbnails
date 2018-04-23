import { vec3, mat4 } from 'gl-matrix';

// ----------------------------------------------------------------------------

function cross(x, y, out) {
  const Zx = x[1] * y[2] - x[2] * y[1];
  const Zy = x[2] * y[0] - x[0] * y[2];
  const Zz = x[0] * y[1] - x[1] * y[0];
  out[0] = Zx;
  out[1] = Zy;
  out[2] = Zz;
}

// ----------------------------------------------------------------------------

function dot(x, y) {
  return x[0] * y[0] + x[1] * y[1] + x[2] * y[2];
}

// ----------------------------------------------------------------------------

function norm(x) {
  return Math.sqrt(x[0] * x[0] + x[1] * x[1] + x[2] * x[2]);
}

// ----------------------------------------------------------------------------

function normalize(x) {
  const den = norm(x);
  if (den !== 0.0) {
    x[0] /= den;
    x[1] /= den;
    x[2] /= den;
  }
  return den;
}

// ----------------------------------------------------------------------------

function copy(src, dst) {
  dst[0] = src[0];
  dst[1] = src[1];
  dst[2] = src[2];
}

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

    this.container.style.overflow = 'hidden';
    this.container.appendChild(this.image);
    this.container.addEventListener('mousemove', this.onMouseMove);
  }

  orthogonalizeViewUp() {
    cross(this.position, this.viewUp, direction);
    cross(direction, this.position, this.viewUp);
    normalize(this.viewUp);
    normalize(this.position);
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
    cross(this.viewUp, this.position, v2);
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

    copy(newCamPos, this.position);

    newViewUp[0] -= newCamPos[0];
    newViewUp[1] -= newCamPos[1];
    newViewUp[2] -= newCamPos[2];
    copy(newViewUp, this.viewUp);
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

    copy(newCamPos, this.position);
    newViewUp[0] -= newCamPos[0];
    newViewUp[1] -= newCamPos[1];
    newViewUp[2] -= newCamPos[2];
    copy(newViewUp, this.viewUp);
    this.orthogonalizeViewUp();
    this.updateImage();
  }

  updateImage() {
    if (!this.image) {
      return;
    }

    copy(this.position, newCamPos);
    let theta = snap(
      Math.asin(newCamPos[1]) * 180 / Math.PI + 90,
      this.angleStep
    );
    newCamPos[1] = 0;
    normalize(newCamPos);
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
    cross(originalViewUp, originalPosition, originalViewUp);
    cross(originalPosition, originalViewUp, originalViewUp);
    normalize(originalViewUp);

    const correctedViewUp = [0, 0, 0];
    cross(this.viewUp, originalPosition, correctedViewUp);
    cross(originalPosition, correctedViewUp, correctedViewUp);
    normalize(correctedViewUp);

    const crossV = [0, 0, 0];
    cross(originalViewUp, correctedViewUp, crossV);
    const sign = Math.sign(dot(crossV, originalPosition));

    const cosT = dot(originalViewUp, correctedViewUp);
    const angle = sign * Math.round(Math.acos(cosT) * 180 / Math.PI);

    this.image.src = `${this.basepath}/${theta}_${phi}.jpg`;
    this.image.style.transform = `rotate(${angle}deg)`;
  }
}
