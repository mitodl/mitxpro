// @flow
import Decimal from "decimal.js-light";
import * as R from "ramda";
import { equals } from "ramda";
import moment from "moment";

import type {
  BasketItem,
  CouponSelection,
  Product,
} from "../flow/ecommerceTypes";
import {
  COUPON_TYPE_PROMO,
  PRODUCT_TYPE_COURSERUN,
  DISCOUNT_TYPE_PERCENT_OFF,
  DISCOUNT_TYPE_DOLLARS_OFF,
} from "../constants";
import type { Course, CourseRun } from "../flow/courseTypes";

export const calculateDiscount = (
  item: BasketItem,
  coupon: ?CouponSelection,
): Decimal => {
  if (coupon && coupon.targets.includes(item.id)) {
    if (coupon.discount_type === DISCOUNT_TYPE_PERCENT_OFF) {
      return new Decimal(coupon.amount)
        .times(new Decimal(item.price))
        .toFixed(2, Decimal.ROUND_HALF_UP);
    } else if (coupon.discount_type === DISCOUNT_TYPE_DOLLARS_OFF) {
      return coupon.amount;
    }
  }

  return new Decimal(0);
};

export const calculatePrice = (
  item: BasketItem,
  coupon: ?CouponSelection,
): Decimal => {
  const price = new Decimal(item.price).minus(calculateDiscount(item, coupon));
  if (price < 0) {
    return 0;
  } else {
    return price;
  }
};

export const calculateTax = (
  item: BasketItem,
  coupon: ?CouponSelection,
  taxRate: number,
): Decimal => {
  const priceAfterDiscount = calculatePrice(item, coupon);
  return taxRate ? priceAfterDiscount * (taxRate / 100) : 0;
};

export const calculateTotalAfterTax = (
  item: BasketItem,
  coupon: ?CouponSelection,
  taxRate: number,
): Decimal => {
  const priceAfterDiscount = calculatePrice(item, coupon);
  const taxAmount = calculateTax(item, coupon, taxRate);
  return priceAfterDiscount.add(taxAmount);
};

const determinePreselectRunTag = (
  item: BasketItem,
  preselectId: number = 0,
): ?string => {
  if (preselectId && item.courses.length > 0) {
    const matchingPreselectRun = item.courses[0].courseruns.find(
      (run) => run.id === preselectId,
    );
    if (matchingPreselectRun && matchingPreselectRun.run_tag) {
      return matchingPreselectRun.run_tag;
    } else {
      return null;
    }
  }
  if (item.run_tag) {
    return item.run_tag;
  }
  return null;
};

export const calcSelectedRunIds = (
  item: BasketItem,
  preselectId: number = 0,
): { [number]: number } => {
  if (item.type === PRODUCT_TYPE_COURSERUN) {
    const course = item.courses[0];
    return {
      [course.id]: item.object_id,
    };
  }

  const preselectRunTag = determinePreselectRunTag(item, preselectId);
  if (!preselectRunTag) {
    return {};
  }

  const numCourses = item.courses.length;
  const courseRunSelectionMap = {};
  for (const course of item.courses) {
    const matchingRun = course.courseruns.find(
      (run) => run.run_tag === preselectRunTag,
    );
    if (matchingRun) {
      courseRunSelectionMap[course.id] = matchingRun.id;
    }
  }
  return Object.keys(courseRunSelectionMap).length === numCourses
    ? courseRunSelectionMap
    : {};
};

export const formatNumber = (
  number: ?string | number | Decimal,
  trimTrailingZeros: boolean = true,
): Decimal => {
  if (number === null || number === undefined) {
    return "";
  } else {
    let formattedNumber: Decimal = Decimal(number);

    if (formattedNumber.isInteger() && trimTrailingZeros) {
      formattedNumber = formattedNumber.toFixed(0);
    } else {
      formattedNumber = formattedNumber.toFixed(2, Decimal.ROUND_HALF_UP);
    }
    return formattedNumber;
  }
};

export const formatPrice = (
  price: ?string | number | Decimal,
  trimTrailingZeros: boolean = false,
): string => {
  let formattedPrice = formatNumber(price, trimTrailingZeros);
  if (formattedPrice) {
    formattedPrice = `$${formattedPrice}`;
  }
  return formattedPrice;
};

export const formatDiscount = (
  discount: ?string | number | Decimal,
  trimTrailingZeros: boolean = false,
): string => {
  if (discount === null || discount === undefined) {
    return "$0.00";
  }

  let formattedDiscount = formatNumber(discount, trimTrailingZeros);

  // eslint-disable-next-line eqeqeq
  if (formattedDiscount == 0) {
    return `$${formattedDiscount}`;
  } else if (formattedDiscount < 0) {
    formattedDiscount = (formattedDiscount * -1).toFixed(2);
  }
  // $FlowFixMe: formatted_discount is a Decimal here
  return `-$${formattedDiscount}`;
};

export const formatCoursewareDate = (dateString: ?string) =>
  dateString ? moment(dateString).format("ll") : "?";

export const formatRunTitle = (run: ?CourseRun) =>
  run
    ? `${formatCoursewareDate(run.start_date)} - ${formatCoursewareDate(
        run.end_date,
      )}`
    : "";

export const isPromo = equals(COUPON_TYPE_PROMO);

export const findProductById = (
  products: Array<Product>,
  id: number | string,
): ?Product => {
  if (isNaN(id)) {
    return products.find(
      (product) => product.latest_version.readable_id === id,
    );
  } else {
    return products.find((product) => product.id === parseInt(id));
  }
};

export const findRunInProduct = (product: Product): [?CourseRun, ?Course] => {
  if (product.product_type !== PRODUCT_TYPE_COURSERUN) {
    // Calling functions are responsible for checking this
    throw new Error("Expected a run product");
  }

  const productVersion = product.latest_version;
  const runId = productVersion.object_id;

  for (const course of productVersion.courses) {
    for (const run of course.courseruns) {
      if (run.id === runId) {
        return [run, course];
      }
    }
  }

  // This should be prevented by the REST API
  return [null, null];
};
